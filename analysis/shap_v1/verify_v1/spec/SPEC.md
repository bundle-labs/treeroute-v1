# Round 14 spec: results format and open choices

Independent re-computation of the SHAP comparison numbers of scope (i) (lead 0 of coral, fire, pm25, defo and ndvi)
and of treeroute's B1 sensitivity. Two implementers (A and B) each recompute every number with their own code, written
from the protocol's words; a reconciler compares A, B and the official outputs of `compare_shap.py` (B1: A with B).

Names: SHAP = `D:\treeroute\analysis\shap_v1`; V = `SHAP\verify_v1`; ROOT = the research-paper folder; `<p>` = a
problem (coral, defo, fire, pm25, ndvi); `<X>` = an implementer (A or B); "piece" = one model folder
`SHAP\out\<p>\lead_0\<model>\`; "the brief" = `V\_brief\brief_verify.md`; "the protocol" = `SHAP\PROTOCOL.md`.

**What this spec does and does not do.** It fixes the FORMAT of the results (section 2, with
`V\spec\results_schema.json`) and lists the places where the protocol's words leave a choice open (section 3). It
makes no choice for the implementers and says nothing about how to compute any number. Where it quotes the protocol,
the quote is the specification; where it describes a key, the description names the number, it does not define it.
The ground truth for the method is the brief's section "Ground truth for the method": the protocol's sections 8
(frozen; it defines every statistic), 5, 9 and 10.

Contents: 1 Inventory - 2 Results format - 3 Open choices and identifications - 4 What each implementer also
writes - 5 Tools in `V\spec\tools` - 6 What the spec writer opened.

---

## 1. Inventory (names only)

### 1.1 Models (per_lead.json structural keys)

From `SHAP\out\<p>\lead_0\compare\per_lead.json`, keys `models`, `main_set`, `declined_by_guard`, `links`, `rows`
(printed by `V\spec\tools\inspect_structure.py`; lists in the file's order):

| problem | models | main_set | declined_by_guard | rows | pairs per level |
|---|---|---|---|---|---|
| coral | rival_hgb_l1, rival_lgbm, rival_lgbm_tweedie, rival_rf, rival_ridge, treeroute | rival_hgb_l1, rival_lgbm, rival_rf, treeroute | (empty) | 1000 | 15 |
| defo | rival_lgbm, rival_lgbm_tweedie, rival_rf, rival_ridge, treeroute | rival_lgbm, rival_rf, rival_ridge, treeroute | (empty) | 1000 | 10 |
| fire | rival_lgbm, rival_lgbm_tweedie, rival_rf, rival_ridge, treeroute | treeroute | rival_ridge | 1000 | 10 |
| pm25 | rival_lgbm, rival_rf, rival_ridge, treeroute | rival_lgbm, rival_rf, rival_ridge, treeroute | (empty) | 1000 | 6 |
| ndvi | rival_bardl_h1, rival_lgbm, rival_rf, rival_ridge, treeroute | rival_bardl_h1, rival_lgbm, rival_rf, rival_ridge, treeroute | (empty) | 1000 | 10 |

`links` (model -> link string):

- coral: rival_hgb_l1, rival_lgbm, rival_rf, treeroute -> `arcsine|c=0.1084375|ub=100`; rival_lgbm_tweedie ->
  `log_mu|c=0.1084375|ub=100`; rival_ridge -> `log_c|c=0.1084375|ub=100`.
- defo: rival_lgbm, rival_rf, rival_ridge, treeroute -> `log_c|c=4.95638378197e-05|ub=1`; rival_lgbm_tweedie ->
  `log_mu|c=4.95638378197e-05|ub=1`.
- fire: treeroute -> `arcsine|c=0.012987012987|ub=1`; rival_lgbm, rival_rf, rival_ridge ->
  `log_c|c=0.012987012987|ub=1`; rival_lgbm_tweedie -> `log_mu|c=0.012987012987|ub=1`.
- pm25: all four -> `log_c|c=1.5|ub=-`.
- ndvi: all five -> `identity|c=-|ub=1`.

Other structural keys: `sample_sha256` and `draws_sha256` (64 lower-case hex characters each; not copied here: each
implementer reads them from the file). per_lead.json holds no key whose name contains "map"; every piece's
`meta.json` holds `variable_map`, `players` and `variables`. per_lead.json has further top-level keys, which the spec
writer did not print and which the brief forbids reading.

`models` lists `treeroute_B1` in no problem (brief item 9 asks each implementer to check this).

The draw matrices `SHAP\out\<p>\lead_0\compare\bootstrap_draws.npy` (shape and dtype only, `np.load(mmap_mode='r')`):

| problem | shape | dtype |
|---|---|---|
| coral | (2000, 37) | int64 |
| defo | (2000, 42) | int64 |
| fire | (2000, 40) | int64 |
| pm25 | (2000, 127) | int64 |
| ndvi | (2000, 133) | int64 |

### 1.2 Pieces and their files

`SHAP\out\<p>\lead_0\`:

| problem | pieces (besides `compare\`) |
|---|---|
| coral | rival_hgb_l1, rival_lgbm, rival_lgbm_tweedie, rival_rf, rival_ridge, treeroute |
| defo | rival_lgbm, rival_lgbm_tweedie, rival_rf, rival_ridge, treeroute, treeroute_B1 |
| fire | rival_lgbm, rival_lgbm_tweedie, rival_rf, rival_ridge, treeroute, treeroute_B1 |
| pm25 | rival_lgbm, rival_rf, rival_ridge, treeroute, treeroute_B1 |
| ndvi | rival_bardl_h1, rival_lgbm, rival_rf, rival_ridge, treeroute, treeroute_B1 |

Files of a piece:

- every `rival_*`: `background_keys.parquet`, `exactness.json`, `meta.json`, `rows.parquet`, `rows.parquet.done.json`;
  `rival_ridge` of defo, fire, pm25 and ndvi also `ridge_shap_exactness.json`;
- `treeroute` and `treeroute_B1`: `background_keys.parquet`, `meta.json`, `rows.parquet`, `rows.parquet.done.json`.

`compare\` of every problem: `AW3_table.md`, `AW4_main_row.json`, `AW4_table.md`, `bootstrap_draws.npy`,
`bootstrap_stats.parquet`, `families.parquet`, `importance.parquet`, `pairs.parquet`, `pairs.parquet.done.json`,
`per_lead.json`.

Also present: `SHAP\out\<p>\RUN_SUMMARY_scope_i.json` (one per problem), and `SHAP\sample\<p>\` with `sample.parquet`,
`sample_manifest.json` and `background_lead_<L>.parquet` (coral L = 0, 183, 365; defo 0, 1; fire, pm25, ndvi 0, 6, 12).
The spec writer opened none of these.

### 1.3 The B1 pieces

`SHAP\out\<p>\lead_0\treeroute_B1\`:

| problem | folder | files |
|---|---|---|
| coral | absent (section 5: "Not defined for coral.") | - |
| defo | present | background_keys.parquet, meta.json, rows.parquet, rows.parquet.done.json |
| fire | present | background_keys.parquet, meta.json, rows.parquet, rows.parquet.done.json |
| pm25 | present | background_keys.parquet, meta.json, rows.parquet, rows.parquet.done.json |
| ndvi | present | background_keys.parquet, meta.json, rows.parquet, rows.parquet.done.json |

No `FAILED.json` is in any of them (file names as listed on 2026-11-16). Each implementer establishes the status
itself (brief item 9, first sub-item).

### 1.4 Row-file columns (`rows.parquet`, schema only)

Every one of the 29 row files (the pieces of 1.2) has 1000 rows (parquet footer) and these 13 columns besides the
attribution columns, with these types:

`row` int64, `unit` string, `group` string, `time` int64, `year` int64, `base` double, `eta` double, `eta_model`
double, `pre` double, `resid` double, `gap` double, `add_err` double, `resid_flag` bool.

Attribution columns (all double):

- feature level: `phi__<player>`, where `<player>` is `x__<name>`, `c__<name>` or `normal`;
- variable level: `phiv__<variable>`, where `<variable>` is a stripped name (for example `hist_last`, `cool`, `CTI`),
  `calendar`, `ctx:<name>` or `normal`.
- The brief names "the B1 run's tree player and context player of that column (`phi__x__<v>` and
  `phi__c__ctx:top5:<v>`)". No row file of this round has a column whose name starts with `phi__c__ctx:top5:`.

Per problem and piece (counts of columns; the non-`x__` names in full):

| problem | piece(s) | phi__ | of which phi__x__ | phi__c__ names | phi__normal | phiv__ | phiv__ names that are calendar, ctx:*, hist_*, normal |
|---|---|---|---|---|---|---|---|
| coral | the five rival_* | 69 | 63 | c__ctx_month, c__ctx_doy_sin, c__ctx_doy_cos, c__ctx_abslat, c__ctx_mmm | yes | 26 | calendar, ctx:abslat, ctx:mmm, normal |
| coral | treeroute | 68 | 63 | (the same five) | no | 25 | calendar, ctx:abslat, ctx:mmm |
| defo | all six | 309 | 308 | (none) | yes | 121 | hist_last, hist_mean, normal |
| fire | all six | 134 | 131 | c__ctx:month, c__ctx:lat | yes | 117 | calendar, ctx:lat, hist_last, hist_mean, normal |
| pm25 | all five | 125 | 122 | c__ctx:month, c__ctx:lat | yes | 111 | calendar, ctx:lat, hist_last, hist_mean, normal |
| ndvi | rival_bardl_h1 | 10 | 9 | (none) | yes | 4 | hist_last, normal |
| ndvi | the other five | 503 | 498 | c__ctx:sin1, c__ctx:cos1, c__ctx:sin2, c__ctx:cos2 | yes | 117 | calendar, hist_last, hist_mean, normal |

- rival_bardl_h1's columns in full: `phi__x__hist_last_1`, `phi__x__hist_last_2`, `phi__x__hist_last_3`,
  `phi__x__V02_total_precip_mm`, `phi__x__V02_total_precip_mm_lag1`, `phi__x__V02_total_precip_mm_lag2`,
  `phi__x__V30_soil_moisture_pct`, `phi__x__V30_soil_moisture_pct_lag1`, `phi__x__V30_soil_moisture_pct_lag2`,
  `phi__normal`; `phiv__hist_last`, `phiv__normal`, `phiv__soil_moisture_pct`, `phiv__total_precip_mm`. All of its
  names occur in NDVI's other pieces.
- Examples of other names: `phi__x__cool_30`, `phiv__cool` (coral); `phi__x__V01_mean_temp_C_max` (defo);
  `phi__x__V01_mean_temp_C`, `phi__x__V01_mean_temp_C_lag1` (ndvi); `phiv__CTI`, `phiv__aet_total_mm` (defo, fire,
  pm25, ndvi).
- The `phi__` columns are in sorted order in no piece; in fire, pm25 and ndvi the rivals' order differs from
  treeroute's (coral and defo: the same order for the names the pieces share). The `phiv__` columns are in sorted order
  in every piece. No row file repeats a column name.
- No `phi__`/`phiv__` name in any row file contains `|`, `/` or `\`, or ends with `_why` (checked over all 8,948
  attribution column names), so the key rules of section 2 are unambiguous.
- `meta.json` key `duplicates_merged`: in NDVI's treeroute, treeroute_B1, rival_lgbm, rival_rf and rival_ridge it has
  five keys, `c__ctx:top5:V01_mean_temp_C`, `c__ctx:top5:V07_total_ref_ET_mm_lag1`, `c__ctx:top5:era5l_d2m`,
  `c__ctx:top5:era5l_slhf_lag1` and `c__ctx:top5:sph_kgkg_lag6` (string values); in every other piece it is empty.

### 1.5 Key names of meta.json and rows.parquet.done.json

- `meta.json`, every piece: `all_finite`, `background`, `background_keys_sha256`, `c`, `checks_passed` (keys `S-ADD`,
  `S-EVAL`, `S-RESID`, `S-ZERO`, boolean values), `duplicates_merged`, `guard`, `lead`, `link`,
  `max_abs_additivity_error`, `max_abs_additivity_error_variable`, `max_abs_background_evaluator_minus_model`,
  `max_abs_eta_minus_base`, `max_abs_resid`, `max_unattributed_share`, `model`, `pass`, `players` (list),
  `players_nonzero`, `problem`, `rows`, `rows_flagged_resid`, `rows_sha256`, `sample_sha256`,
  `structural_zero_violation_players`, `structural_zero_violations`, `tolerances`, `ub`, `value_function`,
  `variable_map` (one entry per player), `variables` (list), `variables_nonzero`; most pieces also
  `max_abs_evaluator_minus_model`.
  - treeroute and treeroute_B1 also: `arm`, `checks`, `corrector_arm`, `d8_licence`, `kind`, `pairs`,
    `rebuild_e8_bit_identical`, `tree_shap_seconds`, `trees_used` (defo's also `max_abs_gap_float32_dot`,
    `max_gap_over_bound`).
  - rivals also `exactness` and `shap_seconds` or `seconds`; rival_ridge and rival_bardl_h1 further keys.
  - The eight fields of brief item 9 (`pass`, `checks_passed`, `rows`, `background`, `pairs`, `trees_used`,
    `sample_sha256`, `duplicates_merged`) are present in each B1 `meta.json`, beside `players_nonzero`,
    `variables_nonzero` and `tree_shap_seconds`.
- `rows.parquet.done.json`, every piece: `background_keys_sha256`, `bytes`, `file`, `finished`, `inputs`,
  `sample_sha256`, `seconds`, `sha256` (rival_ridge of defo, fire, pm25 and ndvi also `script`).

### 1.6 Other records named by the brief (not opened by the spec writer)

- `SHAP\RUN_COMMANDS.md` section 2 ("Treeroute's B1 sensitivity has its own command"): the B1 command and its status.
- `SHAP\SAMPLE_REGISTER.txt`: the registered samples (brief item 9: B1's `sample_sha256` "must be the registered one").
- `SHAP\logs\tr_shap_<p>_lead0.log`: the main and the B1 lines, one after the other, with no B1 label; the B1 lines are
  those written from 2026-11-15 23:06 (the brief).

### 1.7 Reading rules for the implementers (the brief's, restated)

Before its results are written, an implementer reads none of: `SHAP\scripts\compare_shap.py`,
`SHAP\scripts\shapv1_stats.py`, the compare outputs (`AW3_table.md`, `AW4_table.md`, `AW4_main_row.json`,
`pairs.parquet`, `importance.parquet`, `families.parquet`, `bootstrap_stats.parquet`), per_lead.json beyond its
structural keys (models, main_set, declined_by_guard, links, rows, sample_sha256, the draws' SHA-256 and the maps of
players to variables and families if it holds them), and the other implementer's folder. Reading the protocol, the row
files, `meta.json`, `bootstrap_draws.npy` and the run records is allowed; so are the B1 pieces and the logs. Never open
`SHAP\smoke\bardl_fix\`. The compare folder also holds `pairs.parquet.done.json`, which the brief's list does not name;
this spec's writer was forbidden every compare file except `per_lead.json` and `bootstrap_draws.npy`, and so read none
of it. Python: `py -3.9 -I -B <script>`; no pip, no new packages (numpy, pandas, pyarrow, scipy); read-only on every
existing file; keep each script run under about 20 minutes; never write memmaps column by column.

---

## 2. Results format

### 2.1 The file

One file per implementer: `V\<X>\results.json`. UTF-8 without a byte-order mark; strict JSON (no `NaN`, `Infinity` or
`-Infinity` tokens; for example Python `json.dump(..., allow_nan=False)`); indentation free. It must validate against
`V\spec\results_schema.json` (JSON Schema draft-07) and pass `V\spec\tools\validate_results.py` (section 5). The
reconciler matches every number by its JSON path.

### 2.2 Conventions

1. **Names.** Model names as in per_lead.json (`treeroute`, `rival_lgbm`, ...; B1's run is `treeroute_B1`). A player
   is its `phi__` column name without the prefix `phi__` (for example `x__V01_mean_temp_C`, `c__ctx:month`,
   `normal`); a variable is its `phiv__` column name without the prefix `phiv__` (for example `hist_last`,
   `calendar`, `ctx:lat`, `normal`). A B1 player formed by summing a merged context column is named as in the main
   run (`x__<v>`), as the brief says.
2. **Pair keys.** The two model names in alphabetical order (Python string order) joined by `|`, for example
   `rival_lgbm|treeroute`; B1's pair is `treeroute|treeroute_B1`.
3. **Order of lists.**
   - Copies of per_lead.json lists (`models`, `main_set`, `declined_by_guard`, and `main_row.main_set`): the file's
     order.
   - Rank lists (`ranking`, `main_ranking`, `top10`, `top3`, `treeroute_top3`, `consensus_top3`): rank order, rank 1
     first.
   - `draws.regions_in_draw_order`: the order the draw integers refer to.
   - Every other list of names or row numbers (`J`, `structural_zeros`, `top20_union`, `sign_union_top10`,
     `sign_determined_both`, `global_indices`, `test_set_columns`, `rivals`, `models_covered`, `declined`, and the
     `*_only_in_*`, `duplicates_merged_*` and `context_columns_summed` lists of `b1`): sorted ascending (Python
     `sorted()`). This sorting is presentation only; it is not a tie rule.
4. **Numbers.** Plain JSON numbers at full precision: float64 values written as Python's `json` writes them (the
   shortest repr that reads back to the same float). No rounding, no fixed decimals, no strings. Counts outside an
   interval object are integers.
5. **Undefined numbers.** `null`, with a sibling key `<key>_why` (one plain sentence) in the same object. A statistic
   undefined by its definition (for example Kendall's W of a main set of one model, a top-20 Jaccard whose condition
   fails, the pair numbers of fire's main row) is the statistic's key set to null, with its `_why`. A statistic that is
   defined but not finite on the full sample is an interval object whose `value` is null, with `value_why`. In a map
   keyed by a name (`per_problem.stability`), the sibling of a null entry `<name>` is `<name>_why`. Every other null
   in the file has its `_why` too (the schema and the validator check this).
6. **The interval object** `{"value", "ci_low", "ci_high", "n_finite"}` is the format of every number that may carry
   an interval (brief: "Each number that has an interval carries value, ci_low, ci_high and n_finite"):
   - `value`: the number on the full sample (the sample as it is, every region once);
   - `ci_low`, `ci_high`: the ends of the percentile 95% interval over the 2,000 draws;
   - `n_finite`: the number of the 2,000 draws on which the number is finite (brief: "percentile 95% intervals with
     their number of finite replicates").
   - A number that has no interval by the implementer's reading (C07, C08, C20, C25) carries `ci_low`, `ci_high` and
     `n_finite` null, each with its `_why`. The format does not decide which numbers get an interval.
7. **Top-k lists**: `[[name, share], ...]` in rank order, `share` being the full-sample share (a plain number); at most
   k entries; no interval for a top-k list.
8. **`extra`**: an optional object, allowed in most objects, for the implementer's own diagnostics. The reconciler does
   not match it, and the validator does not check inside it.

### 2.3 Top level

| key | meaning |
|---|---|
| `schema_version` | `"round14_results_v1"` |
| `implementer` | `"A"` or `"B"` |
| `written_at` | ISO 8601 time the file was written, for example `2026-11-16T14:05:00+01:00` |
| `software` | versions used: `python`, `numpy` (required), and any of `pandas`, `pyarrow`, `scipy` used |
| `choices` | one short line per open choice and identification of section 3: keys `C01`-`C25` and `I01`-`I06` (all required), plus `X01`, `X02`, ... for further choices the implementer found; the full entries are in `V\<X>\choices.md` |
| `problems` | keys `coral`, `defo`, `fire`, `pm25`, `ndvi`: brief items 1-8 (2.4) |
| `b1` | keys `coral`, `defo`, `fire`, `pm25`, `ndvi`: brief item 9 (2.5) |
| `notes` | optional free text |

### 2.4 `problems.<p>` (brief items 1-8)

| key | meaning |
|---|---|
| `lead` | `0` |
| `models`, `main_set`, `declined_by_guard`, `links`, `rows` | copied from per_lead.json's keys of the same names |
| `draws` | the saved draw matrix and its check (item 6), below |
| `levels.feature`, `levels.variable` | items 1-5 at the feature and the variable level, below |
| `main_row` | item 7 (variable level), below |
| `nonzero_forecast` | item 8, below |

**`draws`** (item 6: "the saved draw matrix `compare\bootstrap_draws.npy` (check its SHA-256 against per_lead.json)"):

| key | meaning |
|---|---|
| `path` | short path of the matrix, `SHAP\out\<p>\lead_0\compare\bootstrap_draws.npy` |
| `shape`, `dtype` | as loaded, for example `[2000, 37]`, `"int64"` |
| `sha256_computed` | the SHA-256 the implementer computed (64 lower-case hex characters) |
| `sha256_covers` | which bytes it covers (I03) |
| `sha256_per_lead` | per_lead.json key `draws_sha256` |
| `sha256_match` | whether the two are equal |
| `region_source` | where a row's region is read (I01) |
| `regions_in_draw_order` | the regions in the order the draw integers refer to (I02) |
| `npz` | short path of this problem's per-draw file, `V\<X>\draws\<p>.npz` (section 4.4) |

**`levels.<L>`**, `<L>` = `feature` or `variable`:

| key | meaning |
|---|---|
| `active_set.J` | item 1: the active set J, "the players to which some model gives more than 1e-12 of its total mean \|phi\|" |
| `active_set.n_J` | its number of players (interval object; C08) |
| `active_set.structural_zeros` | item 1: "The others are listed as structural zeros" |
| `models.<m>` | item 2, one entry per model of `models` (below) |
| `pairs.<a\|b>` | item 4, one entry per pair of models of `models` (below) |
| `per_problem` | item 5 (below) |
| `families` | variable level only: item 3's family map (below) |

**`levels.<L>.models.<m>`** (item 2: "I_m(j) = region-weighted mean |phi_ij| (each region weighs 1), shares s_m(j),
signed mean S_m(j), the number of nonzero players; its top-10 with shares"):

| key | meaning |
|---|---|
| `players.<j>.I` | I_m(j), interval object |
| `players.<j>.share` | s_m(j) = I_m(j) / sum over J, interval object |
| `players.<j>.signed_mean` | S_m(j), the signed mean, interval object |
| `players.<j>.sign_determined` | whether the sign of S_m(j) is determined (section 8: "determined: the bootstrap 95% interval of the signed mean excludes 0"), by the implementer's rule (C17); true, false, or null with why |
| `n_nonzero` | "the number of nonzero players" (C09), interval object |
| `ranking` | the model's ranking over J, rank order, under the implementer's reading of section 8's tie rule (C10) |
| `top10` | its top-10 with shares (2.2 item 7) |
| `family_shares.<f>` | item 3: "each model's family shares", interval objects; required at the variable level, optional at the feature level (C15) |

`players` holds one entry per player of J (variables at the variable level) for which the implementer gives the model
a value (C06). The family keys `<f>` are `own_history`, `global_indices`, `local_drivers`, `context_and_calendar` and
`seasonal_normal` (section 8: "own history (`hist_*`), global indices (...), local drivers, context and calendar, the
seasonal normal").

**`levels.variable.families`** (item 3):

| key | meaning |
|---|---|
| `variable_family` | every variable the implementer classifies -> one of the five family keys |
| `global_indices` | the variables classified as global indices (section 8's rule; I04, C16) |
| `test_set_records` | short paths of the records read to find "the lead's test set" (I04) |
| `test_set_columns` | the columns read from them |

**`levels.<L>.pairs.<a|b>`** (item 4: "Every pair (same-link and cross-link labelled)"):

| key | meaning |
|---|---|
| `models` | `[a, b]`, the key's order |
| `link_class` | `"same-link"` or `"cross-link"` (section 8: "A pair is same-link when both models explain in the same link space (same link, c and ub), else cross-link") |
| `cross_link_label` | present only on a cross-link pair: `"not comparable in scale or rank"` (section 8) |
| `declined` | the pair's models listed in `declined_by_guard` (section 10: "declined rivals labelled"); `[]` when none |
| `both_in_main_set` | whether both models are in `main_set` |
| `spearman_J` | Spearman's rho over J |
| `spearman_top20_union` | Spearman's rho over the union of the two top-20 sets |
| `top20_union` | that union (full sample) |
| `kendall_tau_b` | Kendall's tau-b |
| `jaccard_top5`, `jaccard_top10` | Jaccard similarity of the top-5 and of the top-10 sets |
| `jaccard_top20` | Jaccard similarity of the top-20 sets "when J has 200 or more players"; otherwise null with why |
| `rbo_p090`, `rbo_p095` | RBO on the full rankings over J, p = 0.9 and p = 0.95 |
| `tv_shares` | the total-variation distance between the two models' shares |
| `tv_family_shares` | the total-variation distance between their family shares (feature level: C15) |
| `sign_agreement` | sign agreement of S_m on the union of the two top-10 sets, among the players whose sign is determined in both models (C17) |
| `sign_n_determined` | "with that count": the number of players of that union whose sign is determined in both models |
| `sign_n_agree` | of those players, the number whose two signs agree |
| `sign_union_top10` | the union of the two top-10 sets (full sample) |
| `sign_determined_both` | its players whose sign is determined in both models (full sample) |

Every statistic of a pair is an interval object (or null with why).

**`levels.<L>.per_problem`** (item 5: "Kendall's W over the main set (tie-corrected); the mean pairwise Spearman of the
main set (computed directly); each model's stability under region resampling"):

| key | meaning |
|---|---|
| `kendall_w` | Kendall's W over the main set with the tie correction |
| `kendall_w_m`, `kendall_w_n` | the number of rankings and the number of players W is computed over (integers, or null with why) |
| `mean_pairwise_spearman` | the mean of the pairwise Spearman correlations of the main set, computed directly |
| `stability.<m>` | each model's stability under region resampling ("the mean Spearman between its full-sample importances and its own bootstrap replicates"), one entry per model of `models` |

**`main_row`** (item 7, variable level; section 8 "Main-text row"):

| key | meaning |
|---|---|
| `level` | `"variable"` |
| `main_set` | "The main set" (copied, per_lead order) |
| `rivals` | treeroute's same-link rivals the row is computed over (`[]` for fire) |
| `kendall_w` | "Kendall's W [CI]" |
| `spearman_top20_union_median` | "treeroute against its same-link rivals: the median of the top-20-union Spearman [CI]" |
| `spearman_top20_union_min`, `spearman_top20_union_max` | "and the range" (C22) |
| `spearman_top20_union_per_rival` | the full-sample top-20-union Spearman of treeroute against each rival (`{rival: number}`; diagnostic) |
| `rbo_p090_vs_consensus` | "RBO (p 0.9) of treeroute against the rivals' consensus (the mean of their shares, rebuilt per draw) [CI]" |
| `consensus_shares` | the full-sample consensus (`{variable: number}`; diagnostic) |
| `treeroute_top3` | "treeroute's top 3 variables", `[[name, share], ...]` |
| `consensus_top3` | "the consensus top 3", `[[name, consensus share], ...]` |
| `own_history_share_treeroute` | "the own-history share of treeroute [CI]" (C24) |
| `own_history_share_median_rival` | "and of the median rival [CI]" (C23, C24) |
| `own_history_share_per_rival` | each rival's full-sample own-history share (`{rival: number}`; diagnostic) |
| `median_rival_name` | when the implementer's reading of "the median rival" names one rival: its name; otherwise null with why (C23) |

Fire (brief item 7: "Fire's main set is treeroute alone: W and the pair statistics are undefined there, and
treeroute's top 3 and own-history share still have values"): the keys that need a rival or more than one model are
null with their `_why`; `treeroute_top3` and `own_history_share_treeroute` have values.

**`nonzero_forecast`** (item 8: "Arcsine-link models: the variable-level importances on their rows with a nonzero
forecast (pre > 0)"):

| key | meaning |
|---|---|
| `models_covered` | the arcsine-link models reported here (C25); `[]` when none |
| `models_covered_why` | one sentence: why these models |
| `models.<m>.level` | `"variable"` |
| `models.<m>.rows_used` | the number of the model's rows with pre > 0 |
| `models.<m>.regions_used` | the number of regions with at least one such row |
| `models.<m>.J` | the variables its shares are taken over (C25) |
| `models.<m>.players.<v>` | `I`, `share`, `signed_mean` (interval objects) and `sign_determined` on those rows, as in `levels.<L>.models.<m>.players` |
| `models.<m>.n_nonzero`, `ranking`, `top10` | as in `levels.<L>.models.<m>` |

### 2.5 `b1` (brief item 9)

The brief: "the B1 numbers go under their own top-level key `b1`: per problem `status`; for defo `identity`; for
fire, pm25 and ndvi `run` and, per level (`feature`, `variable`), `importance`, `top10` and `pair_main_b1`, and at the
variable level also `families`, `top3` and `own_history_share`." So:

```
b1.<p>.status                                   every problem (coral included)
b1.defo.identity                                when b1.defo.status.numbers == "identity"
b1.<fire|pm25|ndvi>.run                         when b1.<p>.status.numbers == "full"
b1.<fire|pm25|ndvi>.feature.{importance, top10, pair_main_b1}
b1.<fire|pm25|ndvi>.variable.{importance, top10, pair_main_b1, families, top3, own_history_share}
```

B1 has nothing of item 8 (the brief: "Compute nothing for B1 that it does not list (in particular not item 8, fire's
view on its rows with a nonzero forecast)"), and nothing of B1 is in `problems` (the brief: "put nothing of B1 into
items 1-8").

**`b1.<p>.status`** (item 9, first sub-item, and "Check that per_lead.json's models does not list treeroute_B1"):

| key | meaning |
|---|---|
| `folder_exists` | whether `SHAP\out\<p>\lead_0\treeroute_B1\` exists |
| `has_done_json` | whether it holds `rows.parquet.done.json` |
| `has_failed_json` | whether it holds `FAILED.json` |
| `finished` | whether it is a finished piece (the brief: "holds `rows.parquet.done.json` (a finished piece)") |
| `failed_stop` | for a `FAILED.json`, the stop it records (S-ADD, S-EVAL, S-ZERO or S-RESID); else null with why |
| `meta` | for a finished piece, its `meta.json` fields `pass`, `checks_passed`, `rows`, `background`, `pairs`, `trees_used`, `sample_sha256`, `duplicates_merged`, copied verbatim; else null with why |
| `background_is_B1` | whether `meta.background` is `"B1"` (the brief: "it must be "B1"") |
| `sample_sha256_registered` | the registered sample SHA-256 of this problem's lead 0 in `SHAP\SAMPLE_REGISTER.txt` (I05) |
| `sample_sha256_is_registered` | whether `meta.sample_sha256` equals it |
| `per_lead_models_lists_treeroute_B1` | whether per_lead.json's `models` lists `treeroute_B1` |
| `numbers` | which B1 numbers follow: `"none"`, `"identity"` (defo only) or `"full"` (fire, pm25, ndvi only); coral: `"none"` |
| `numbers_why` | one sentence: which numbers and why (for `"none"`: the brief's "A problem without a finished B1 piece gets no B1 numbers: write which and why"; or that defo's check held the numbers back) |

**`b1.defo.identity`** (item 9: "Defo: only the identity check, with its pairs and seconds"):

| key | meaning |
|---|---|
| `max_abs_diff_phi` | "the largest \|difference\| between `treeroute_B1\rows.parquet` and `treeroute\rows.parquet` over every row and every `phi__` column", rows matched by `row`, players by name |
| `max_abs_diff_phiv` | "the same over the `phiv__` columns" |
| `same_rows`, `same_players`, `same_variables` | "whether the two runs have the same rows, players and variables" |
| `n_rows_main`, `n_rows_b1`, `n_players_main`, `n_players_b1`, `n_variables_main`, `n_variables_b1` | the counts behind them |
| `rows_only_in_main`, `rows_only_in_b1`, `players_only_in_main`, `players_only_in_b1`, `variables_only_in_main`, `variables_only_in_b1` | the differences (empty lists when none) |
| `as_expected` | "Expected: 0 and the same": true when both maxima are 0 and the three sets are the same |
| run facts | the keys of `b1.<p>.run` below from `log_file` to `tree_shap_seconds_meta` |

When `as_expected` is false, the brief's rule applies: "write these numbers and stop the B1 work there: report to the
lead before any other B1 number is computed"; then fire's, pm25's and ndvi's `status.numbers` are `"none"`, with the
reason in `numbers_why`.

**`b1.<p>.run`** (fire, pm25, ndvi; the run facts also inside `b1.defo.identity`):

| key | meaning |
|---|---|
| `log_file` | short path, `SHAP\logs\tr_shap_<p>_lead0.log` |
| `log_setup_line_number`, `log_done_line_number` | 1-based line numbers of the B1 run's set-up line and "done in" line in that log (I06) |
| `pairs_log`, `pairs_meta` | the background pairs, from the set-up line and from `meta.json` (`pairs`) |
| `total_seconds_log`, `total_seconds_done_json` | the total seconds, from the "done in" line and from `rows.parquet.done.json` (`seconds`) |
| `tree_shap_seconds_log`, `tree_shap_seconds_meta` | the tree-SHAP seconds, from the log and from `meta.json` (`tree_shap_seconds`) |
| `duplicates_merged_main`, `duplicates_merged_b1` | the keys of `duplicates_merged` in the main run's and the B1 run's `meta.json` |
| `context_columns_summed` | the players `x__<v>` formed by summing `phi__x__<v>` and `phi__c__ctx:top5:<v>` of the B1 run (the brief's "Merged context columns" step); `[]` when none |
| `draws_sha256_match` | the same draws' SHA-256 check as `problems.<p>.draws.sha256_match` |
| `npz` | short path of the B1 per-draw file, `V\<X>\draws\b1_<p>.npz` |

No log line is copied into the results (a log line may hold paths; the privacy rule).

**`b1.<p>.<L>`** (fire, pm25, ndvi; `<L>` = `feature` or `variable`):

| key | meaning |
|---|---|
| `importance.players.<j>` | the B1 run's I(j), s(j) and S(j) (`I`, `share`, `signed_mean`, interval objects) and `sign_determined`, "with J the pair's J (next sub-item) for the shares", one entry per player of the pair's J |
| `importance.n_nonzero` | the B1 run's number of nonzero players (after any summing of merged context columns) |
| `importance.n_nonzero_before_merge` | feature level only: "also before any summing of the previous sub-item, for the reconciler" |
| `importance.ranking` | the B1 run's ranking over the pair's J, rank order |
| `top10` | the B1 run's top 10 with shares |
| `pair_main_b1` | the pair (the main run, the B1 run), below |
| `families.<f>` | variable level only: the B1 run's family shares (the families and the global-index rule of items 1-3) |
| `top3` | variable level only: its top 3 variables, `[[name, share], ...]` |
| `own_history_share` | variable level only: its own-history share, interval object |

**`b1.<p>.<L>.pair_main_b1`**:

| key | meaning |
|---|---|
| `pair` | `"treeroute\|treeroute_B1"` |
| `J` | the pair's own J: "the players to which either run gives more than 1e-12 of its total mean \|phi\|" |
| `n_J` | its number of players (interval object; C08) |
| `main_shares` | the main run's full-sample shares over this J (`{player: number}`; diagnostic) |
| `main_ranking` | the main run's ranking over this J, rank order |
| the pair statistics | the keys of `levels.<L>.pairs.<a\|b>` from `spearman_J` to `sign_determined_both`, with the same meanings, over this pair's J and for these two runs |

### 2.6 The brief's items and their keys

| brief item | keys |
|---|---|
| 1 Active set J, structural zeros | `problems.<p>.levels.<L>.active_set` |
| 2 I, s, S, nonzero players, top-10 | `problems.<p>.levels.<L>.models.<m>` |
| 3 Families and family shares | `problems.<p>.levels.variable.families`, `problems.<p>.levels.variable.models.<m>.family_shares` |
| 4 Every pair | `problems.<p>.levels.<L>.pairs.<a\|b>` |
| 5 W, mean pairwise Spearman, stability | `problems.<p>.levels.<L>.per_problem` |
| 6 Draws and intervals | `problems.<p>.draws`; every interval object; `V\<X>\draws\<p>.npz` |
| 7 Main-text row | `problems.<p>.main_row` |
| 8 Arcsine models' nonzero forecasts | `problems.<p>.nonzero_forecast` |
| 9 B1 | `b1.<p>`; `V\<X>\draws\b1_<p>.npz` |

---

## 3. Open choices and identifications

Each entry quotes the protocol's (or the brief's) words and states what they leave open. The order and the wording of
the entries imply nothing about any answer. Each implementer makes and records its own choice (section 4.1), and makes
for B1 the choice it makes for the main pairs (the brief: "Wherever the protocol leaves a choice open, make for B1 the
choice you make for the main pairs, and say so"). An implementer who finds a further open choice records it as `X01`,
`X02`, ... in `choices.md` and in `results.json` key `choices`.

### Method choices

**C01 - Rows flagged by S-RESID.** Section 5: "S-RESID: a row whose unattributed part |R_i| + |G_i| exceeds 1% of
|eta_i - base_i| (+1e-9) is flagged; a model with more than 1% flagged rows stops." Section 9 lists "the S-RESID flag"
among the contents of `rows.parquet`. Sections 8 and 10 do not mention flagged rows. Open: whether flagged rows enter
the statistics.

**C02 - Region weights.** Section 8: "I_m(j): the region-weighted mean |phi_ij| (each region weighs 1)"; "A paired
cluster bootstrap over regions: B = 2,000 draws of regions with replacement, the same draws for every model." Open:
what "each region weighs 1" means for the rows within a region; how a region that one draw holds more than once is
weighted.

**C03 - The signed mean.** Section 8: "I_m(j): the region-weighted mean |phi_ij| (each region weighs 1); shares
s_m(j) = I_m(j) / sum over J; the signed mean S_m(j)". Open: the weighting of the signed mean.

**C04 - The threshold of the active set.** Section 8: "Active set J (per level). The players to which some model gives
more than 1e-12 of its total mean |phi|." Section 10 (B1): "the players to which either run gives more than 1e-12 of
its total mean |phi| (section 8's rule, applied to these two runs)". Open: which mean |phi| the rule reads, for a player
and for "its total"; the comparison at exact equality; a model whose total is 0.

**C05 - The models that form J.** Section 8: "The players to which some model gives ..."; the brief: "For each
problem p and the models of per_lead.json key models ...: 1. Active set J (players some model gives more than 1e-12 of
its total mean |phi|) and the structural zeros." Inventory: fire's `declined_by_guard` holds rival_ridge; coral, defo
and fire have cross-link pairs. Open: which models "some model" ranges over (for example every model of `models`,
cross-link and guard-declined models included, or another set); whether one J per level serves every statistic of the
problem.

**C06 - Players with no column in a model's row file; the structural zeros.** Section 8: "The others are listed as
structural zeros (smoke, coral: `normal` and four constant cyclone columns)." Section 5: "The neighbour kind (coral): b
per visit, with 5 standardised context columns and no normal." Section 10: "BARDL reads nine columns by design ... Its
zeros elsewhere mean "not an input". ... Its top-5, top-10 and top-20 sets follow name order beyond its three variables
at the variable level, and beyond its nine columns at the feature level (section 8's tie rule)." Inventory (1.4):
coral's treeroute row file has no `phi__normal` and no `phiv__normal`; NDVI's rival_bardl_h1 has 10 `phi__` and 4
`phiv__` columns. Open: how a player or variable with no column in a model's file enters that model's I, s, S, ranking
and top-k sets; over which set of names the structural zeros are listed.

**C07 - Fixed at the full sample, or found again on each draw.** Section 10: "Where section 8 leaves a choice open (for
example whether J, the top-k sets and the determined signs are fixed at the full sample or found again on each draw, or
whether a count gets an interval), these numbers make the main comparison's choice (`compare_shap.py`), as the
independent re-computation establishes it." Section 8: "The importances, every statistic and every number of the
main-text row are recomputed per draw." Open, for each of J (with the top-20 Jaccard's condition "when J has 200 or
more players"), the top-5, top-10 and top-20 sets, the union of the two top-20 sets, the union of the two top-10 sets,
the determined signs, and B1's pair J: fixed at the full sample, or found again on each draw.

**C08 - Intervals for counts.** Section 10: "or whether a count gets an interval". The counts of the results:
`active_set.n_J`, `n_nonzero` (and B1's `n_nonzero_before_merge`), `sign_n_determined`, `sign_n_agree`, B1's
`pair_main_b1.n_J`. Open: whether each count gets an interval.

**C09 - Nonzero players.** Section 8: "the number of nonzero players"; the brief (item 9): "its number of nonzero
players (at the feature level also before any summing of the previous sub-item, for the reconciler)". Open: what makes
a player nonzero (which quantity, compared with what); among which players the count is taken.

**C10 - Ties and name order.** Section 8: "Spearman's rho on average ranks"; "Kendall's tau-b with the tie
correction"; "Jaccard similarity of the top-5 and top-10 sets (...), ties broken by name"; "RBO on the full rankings
over J (equal length, ties broken by name; ...)". Section 10: "Ties follow section 8's tie rule."; "Its top-5, top-10
and top-20 sets follow name order ...". Open: what counts as a tie (exact equality or within a tolerance; read on I_m
or on s_m); for "name", which string is compared (with or without prefixes such as `x__` and `c__`), in which direction
and collation; whether the same rule orders the top-10 and top-3 lists.

**C11 - Spearman's expression and the top-20 union.** Section 8: "Spearman's rho on average ranks, over J and over the
union of the two top-20 sets". Open: the expression evaluated on average ranks when ties are present; over the union
of the two top-20 sets, whether the ranks are taken within the union or carried from the ranking over J.

**C12 - Size conditions of the top-k sets.** Section 8: "Jaccard similarity of the top-5 and top-10 sets (and top-20
when J has 200 or more players)"; "over the union of the two top-20 sets"; "on the union of the two top-10 sets".
Open: the sets when J has fewer than k players; on which J the 200-player condition is read (the level's J, B1's pair
J; see C07).

**C13 - RBO's form.** Section 8: "RBO on the full rankings over J (equal length, ties broken by name; eq. 32 of
Webber, Moffat and Zobel 2010 reduces to its finite form), p = 0.9 and 0.95"; section 8 (smoke S1): "the RBO closed
form, the case where the nonzero-list RBO of v2 overstated agreement (1.0 against 0.29)". Open: the exact finite
expression evaluated (its terms, the depths it sums over, any normalisation), to be written out in `choices.md`.

**C14 - Total-variation distance.** Section 8: "the total-variation distance between shares (feature or variable
level) and between family shares"; section 10 (B1): "the total-variation distance between the two runs' shares over
this J and between their family shares". Open: the expression (its normalising factor) and the vectors it compares.

**C15 - Family attribution and family shares.** Section 8: "Families, for shares: own history (`hist_*`), global
indices (...), local drivers, context and calendar, the seasonal normal. A family's attribution on a row is the sum of
its variables' (variable-level) phi on that row."; the brief (item 3): "Families at the variable level (...) and each
model's family shares."; section 8 (pairs, "both levels"): "the total-variation distance between shares (feature or
variable level) and between family shares". Open: which of a family's variables are summed on a row (all of them, or
those in J); how a family's importance is formed from its row attributions; the denominator of a family share; a
family with no variable in a problem; whether the feature-level pairs carry a family-share distance, and from which phi.

**C16 - Family membership and the global-index rule.** Section 8: "own history (`hist_*`), global indices (a variable
all of whose columns take one value per time step across every unit of the lead's test set), local drivers, context
and calendar, the seasonal normal"; "context columns are `calendar` (month and harmonics) or `ctx:<name>`"; the brief
(item 3): "'Global indices' needs the lead's test set (section 8's rule): find it from the run's records, read only the
columns you need." Open: the precedence when a variable fits more than one family's description; what "take one value
per time step" means (exact equality or a tolerance, missing values, which time key); "across every unit" when a unit
lacks a time step; a variable some of whose columns the test-set records do not hold.

**C17 - Determined signs and sign agreement.** Section 8: "sign agreement of S_m on the union of the two top-10 sets,
among the players whose sign is determined in both models (determined: the bootstrap 95% interval of the signed mean
excludes 0), with that count." Open: "excludes 0" at the edge (an end exactly 0, an interval of zero width, few finite
replicates); which interval (C21); what the reported sign agreement is (for example a share of the players or a number
of players) and its entry when the count is 0; which signs are compared on a draw (C07).

**C18 - Undefined statistics.** Section 8: "Percentile 95% intervals, each with its number of finite replicates."; the
brief (item 7): "Fire's main set is treeroute alone: W and the pair statistics are undefined there". Open: which inputs
make a statistic undefined (for example a ranking whose values are all tied, an empty set, a zero total), and whether
such a statistic is reported as undefined or given a value, on the full sample and on a draw.

**C19 - Kendall's W and the mean pairwise Spearman.** Section 8: "Kendall's W over the main set with the tie
correction; the mean of the pairwise Spearman correlations of the main set (computed directly: (mW - 1)/(m - 1) is
exact only when every ranking has the same ties)". Open: the players W and the mean are taken over (see C05); the
tie-correction expression; which of the pairwise Spearman correlations (over J, over the top-20 union) the mean
averages.

**C20 - Stability.** Section 8: "each model's stability under region resampling (the mean Spearman between its
full-sample importances and its own bootstrap replicates: descriptive, not a ceiling on between-model agreement)".
Open: the players the Spearman is taken over; how non-finite replicates enter the mean; whether the stability gets an
interval and, if it does, what its per-draw values are.

**C21 - Percentile intervals.** Section 8: "Percentile 95% intervals, each with its number of finite replicates. BCa is
not computed."; the brief (item 6): "percentile 95% intervals with their number of finite replicates". Open: the
percentile definition (the interpolation rule for the 2.5% and 97.5% points); whether non-finite replicates are left
out before the percentiles are taken; the fewest finite replicates for which an interval is given.

**C22 - The main row's median and range.** Section 8: "treeroute against its same-link rivals: the median of the
top-20-union Spearman [CI] and the range"; "every number of the main-text row are recomputed per draw". Inventory:
NDVI's main set has five models, coral's, defo's and pm25's four. Open: the median of an even number of values; how the
median's interval is formed from the draws; what the range reports (its two ends), and whether its ends get intervals.

**C23 - "The median rival".** Section 8: "the own-history share of treeroute [CI] and of the median rival [CI]". Open:
whether this is the median of the rivals' own-history shares, or the own-history share of one rival chosen by a rule
(and which rule); the case of an even number of rivals.

**C24 - The own-history share.** Section 8: "the own-history share of treeroute [CI]"; "Families, for shares: own
history (`hist_*`), ..."; section 10 (B1): "its own-history share". Open: whether it is the own-history family's share
(C15), the sum of the own-history variables' shares s_m(j), or another reading.

**C25 - Arcsine models' nonzero forecasts (item 8).** Section 8: "For every arcsine-link model, the variable-level
importances on its rows with a nonzero forecast (pre > 0) are also reported (fire)."; section 5: "Fire's kept nowcast
is exactly 0 on 75.4% of rows after the arcsine inverse: ... so the comparison also reports each arcsine model's
importances on its rows with a nonzero forecast."; section 10: "arcsine models' nonzero rows"; the brief (item 8):
"Arcsine-link models: the variable-level importances on their rows with a nonzero forecast (pre > 0)." Inventory
(1.1): the arcsine-link models are coral's rival_hgb_l1, rival_lgbm, rival_rf and treeroute, and fire's treeroute.
Open: which problems' arcsine-link models are reported; which numbers "the variable-level importances" are (I, s, S,
counts, top-10) and over which set of variables the shares are taken; the region weighting when a region has no such
row, on the full sample and on a draw; whether these numbers get intervals.

### Identifications (facts each implementer establishes from the records and records with its source)

**I01 - The region of a row.** Section 8: "region-weighted"; section 9: "`rows.parquet`: keys, region, base, eta (our
evaluator), eta_model (the model's own), pre (y units), R, G, the additivity error, the S-RESID flag, phi__<player>
(feature level) and phiv__<variable> (variable level), link space". Inventory (1.4): no column of any row file is named
`region`. To establish: where a row's region is read (key `draws.region_source`).

**I02 - The draw matrix.** Section 8: "B = 2,000 draws of regions with replacement, the same draws for every model. The
draw matrix comes from the SHA-256 generator with the salt `shap_v1|AW4|<problem>|<lead>` and is saved with its
SHA-256." Inventory (1.1): the shapes. To establish: what each integer of the matrix refers to (which list of regions,
in which order) and how the matrix's rows and columns make the draws (key `draws.regions_in_draw_order`).

**I03 - The draws' SHA-256.** Section 9: "`bootstrap_draws.npy` (SHA-256 in `per_lead.json`)"; the brief (item 6):
"check its SHA-256 against per_lead.json". Inventory: per_lead.json key `draws_sha256`. To establish: which bytes the
SHA-256 covers (key `draws.sha256_covers`).

**I04 - The lead's test set.** Section 8 (global indices): "the lead's test set"; the brief (item 3): "find it from the
run's records, read only the columns you need." To establish: which records hold the lead's test set, and which rows
and columns are read (keys `families.test_set_records`, `families.test_set_columns`).

**I05 - The registered sample SHA-256.** The brief (item 9): "`sample_sha256` (it must be the registered one,
`SHAP\SAMPLE_REGISTER.txt`)". To establish: which entry of the register applies to each problem's lead 0 (key
`status.sample_sha256_registered`).

**I06 - The B1 lines of the logs.** The brief: "`SHAP\logs\tr_shap_<p>_lead0.log` holds the main and the B1 lines one
after the other, with no B1 label; the B1 lines are those written from 2026-11-15 23:06"; item 9: "Each B1 run's
(defo's included) background pairs and its total and tree-SHAP seconds, from its log's set-up line and "done in"
line". To establish: how a line's writing time is known; which lines are the B1 run's set-up line and "done in" line;
which numbers on them are the pairs, the total seconds and the tree-SHAP seconds.

---

## 4. What each implementer also writes

Everything in `V\<X>\` (X = A or B); nothing elsewhere.

### 4.1 `V\<X>\choices.md`

One entry per open choice and identification of section 3 (`C01`-`C25`, `I01`-`I06`) and per further choice found
(`X01`, ...), in that order, each with:

- a heading `## C01 <the entry's title>`;
- **Choice:** the choice made (for an identification: what was found, and in which file and field or line);
- **Why:** the reason, from the protocol's words (quote them);
- **B1:** "same as the main pairs", or what differs and why.

The one-line form of each entry goes into `results.json` key `choices`. The entries are written before the
implementer sees any official number, and state no number of the official outputs.

### 4.2 `V\<X>\README.md`

- how to re-run: the exact commands (`py -3.9 -I -B ...`), their order, the working folder, and the time each took;
- every file the code opened, by short path (SHAP\..., V\..., ROOT\...), and every file it wrote;
- the versions of Python, numpy, pandas, pyarrow and scipy used;
- which script computes items 1-8 and which computes item 9, with a statement that the items 1-8 code opens nothing
  under any `treeroute_B1\` folder (the reconciler "confirms that no number of items 1-8 depends on B1");
- the validator's output on the final files (section 5).

### 4.3 Scripts

All of the implementer's scripts, in `V\<X>\scripts\`, runnable as written with `py -3.9 -I -B`. They read only what
section 1.7 allows and write only into `V\<X>\`.

### 4.4 Per-draw values: `V\<X>\draws\<p>.npz` and `V\<X>\draws\b1_<p>.npz`

The per-draw values of every number whose interval object has a non-null `n_finite`, so that interval mismatches can be
diagnosed. One file per problem for `problems.<p>` (`<p>.npz`) and one per problem whose `b1.<p>.status.numbers` is
`"full"` (`b1_<p>.npz`). Written with `numpy.savez` or `numpy.savez_compressed`; readable with
`numpy.load(path, allow_pickle=False)`.

- **Keys.** An entry's key is the number's JSON path below `problems.<p>` (in `<p>.npz`) or below `b1.<p>` (in
  `b1_<p>.npz`), its parts joined by `/`. Examples: `levels/feature/pairs/rival_lgbm|treeroute/spearman_J`,
  `levels/variable/per_problem/kendall_w`, `levels/variable/models/treeroute/family_shares/own_history`,
  `main_row/rbo_p090_vs_consensus`, `variable/pair_main_b1/tv_shares` (in `b1_<p>.npz`).
- **Scalar numbers**: a float64 array of shape (2000,).
- **Per-player numbers** (every `players` map): for the map at path P, three float64 arrays `P/I`, `P/share` and
  `P/signed_mean` of shape (2000, n), and one array `P/names` of n player (or variable) names giving the column order.
  Examples: `levels/feature/models/treeroute/players/I` with `levels/feature/models/treeroute/players/names`;
  `nonzero_forecast/models/treeroute/players/share`; `feature/importance/players/signed_mean` (in `b1_<p>.npz`).
- **Rows**: one row per draw, in the order of the draws in `bootstrap_draws.npy` as I02 establishes it (record that
  order in `choices.md`, entry I02).
- **Values**: NaN where the number is not finite or not defined on that draw. For each number, the count of finite
  values in its array (its column, for per-player numbers) equals its `n_finite` in `results.json` (the validator
  checks this).
- A number whose `n_finite` is null has no entry.

---

## 5. Tools in `V\spec\tools` (format and structure only)

- `inspect_structure.py`, `inspect_names.py`: what the spec writer ran to build section 1 (schemas, key names, the
  structural keys of per_lead.json, the draws' shape and dtype). They print no row value and no statistic.
- `make_schema.py`: writes `V\spec\results_schema.json`; `check_schema.py`: a structural check of that schema (every
  `$ref` resolves, every type name is a draft-07 type, every required key is declared; last run: no problems).
- `validate_results.py`: checks a `results.json` against the schema (a small draft-07 validator, because the
  `jsonschema` package is not installed) and then checks: every null has its `_why`; the lists of 2.2 item 3 are
  sorted; pair keys are complete, alphabetical and agree with `models`, `declined_by_guard` and `main_set`;
  `ci_low` <= `ci_high`; with `--shap`, the copied per_lead.json keys and `draws_sha256` (it reads only per_lead.json's
  structural keys); with `--draws`, every per-draw entry exists, has the right shape, and has as many finite values as
  `n_finite` says. Warnings (not errors) flag a `link_class` that disagrees with the two link strings, a ranking that
  is not a permutation of J, and a top-10 whose names differ from the ranking's first names, since these depend on
  open choices. It computes no statistic.

```
py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\spec\tools\validate_results.py --results D:\treeroute\analysis\shap_v1\verify_v1\A\results.json --draws D:\treeroute\analysis\shap_v1\verify_v1\A\draws --shap D:\treeroute\analysis\shap_v1
py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\spec\tools\validate_results.py --selftest
```

The self-test builds a synthetic file (made-up names and values, no real data), checks that it passes, and checks that
19 kinds of format error are caught (last run: SELFTEST PASSED).

---

## 6. What the spec writer opened

- Read in full: the brief; `SHAP\PROTOCOL.md` sections 5, 8, 9 and 10 (no other section).
- Listed (names only): `SHAP\out\` (every folder, the compare folders included), `SHAP\sample\`, `V\`.
- Schema only (column names, types, footer row counts): every `rows.parquet` under `SHAP\out\`.
- Key names and value types only: every piece's `meta.json` (plus the key names inside `checks_passed` and
  `duplicates_merged`) and `rows.parquet.done.json`.
- `per_lead.json`: loaded in Python; printed only `models`, `main_set`, `declined_by_guard`, `links`, `rows`,
  `sample_sha256` and `draws_sha256` (and a search for keys whose name contains "map": none).
- `bootstrap_draws.npy`: shape and dtype only (`mmap_mode='r'`).
- Not opened: `compare_shap.py`, `shapv1_stats.py` and every other script; every other file of the compare folders;
  `background_keys.parquet`, the `exactness.json` files, the sample folder's files, `RUN_SUMMARY_scope_i.json`, the
  logs, `SAMPLE_REGISTER.txt`, `RUN_COMMANDS.md`; `SHAP\smoke\bardl_fix\`.
- No statistic was computed and no row value was read.
