# Round 14 reconciler: how every official number is mapped to the results.json keys

Names: SHAP = `D:\treeroute\analysis\shap_v1`; V = `SHAP\verify_v1`; `<p>` = a problem; `<L>` = `feature` or
`variable`; `<m>` = a model of per_lead.json `models`; `<a|b>` = a pair key (the two model names in Python string order
joined by `|`). The code that applies this mapping is `V\reconcile\reconcile.py` (function `official()`); the
flattening of A's and B's files is `V\reconcile\rlib.py` (function `flatten()`).

## 1. Keys and conventions

- A key is a results.json path below the top level, its parts joined by `/`, for example
  `problems/fire/levels/variable/pairs/rival_lgbm|rival_rf/spearman_J/ci_low`.
- An interval object `{value, ci_low, ci_high, n_finite}` is four keys. A statistic that A or B set to null as a whole
  (undefined by its definition) is expanded to the same four keys, each null, so that it meets the official keys.
- A top-k list `[[name, share], ...]` is two keys: `<path>/names` (exact, in rank order) and `<path>/shares`
  (position by position, within the tolerance).
- Sets (`J`, `structural_zeros`, `top20_union`, `sign_union_top10`, `sign_determined_both`, `global_indices`,
  `rivals`, `models_covered`, `declined`, ...) are compared as sets; rank lists (`ranking`, `models`, `main_set`,
  `regions_in_draw_order`, ...) as ordered lists.
- Not matched (text or paths, not numbers): every `*_why`, every `extra`, `path`, `npz`, `region_source`,
  `sha256_covers`, `test_set_records`, `log_file`, `models_covered_why`, `numbers_why`, and the top-level `choices`,
  `software`, `written_at`, `implementer`, `notes`, `schema_version`.
- Tolerance: values and interval bounds within 1e-9 absolute or relative; `n_finite` exactly; booleans, strings, lists,
  sets and top-k names exactly.

How the official files' gaps are written:

- NaN in an official file (value or interval end) is null (not a number, as A and B write an undefined number).
- A number whose official file holds no interval (for example importance.parquet's `mean_abs`): the official source
  has the key `.../value` and lacks `.../ci_low`, `.../ci_high` and `.../n_finite`. Where A or B hold an interval
  there, each of those keys is a mismatch "missing in the official outputs" (never skipped).
- A key that `compare_shap.py` writes nowhere by its own rule is null in the official source (so it matches an
  undefined null of A or B, and mismatches a number):
  - `levels/<L>/pairs/<a|b>/jaccard_top20/*` when the level's J has fewer than 200 players (compare_shap.py line 186);
  - `levels/feature/pairs/<a|b>/tv_family_shares/*` (the family TVD exists at the variable level only, lines 281-295);
  - `levels/<L>/active_set/n_J/{ci_low, ci_high, n_finite}` (J is fixed at the full sample, lines 177-183);
  - fire's main-row keys that need a rival (`spearman_top20_union_median`, `_min`, `_max`, `_per_rival`,
    `rbo_p090_vs_consensus`, `consensus_shares`, `consensus_top3`, `own_history_share_median_rival`,
    `own_history_share_per_rival`, `median_rival_name`): compare_shap.py writes none when there is no same-link
    rival (line 361), and the brief (item 7) says they are undefined. Fire's `treeroute_top3` and
    `own_history_share_treeroute` are NOT given this treatment: they are defined (brief item 7), compare_shap.py does
    not write them, and they count as missing in the official outputs.
- "Official-derived" keys: keys that no official file holds but that follow from official numbers by
  compare_shap.py's own rules. They are a second check only; such a key still counts as missing in the official
  outputs. They are marked "(derived)" below.

## 2. File by file

### `compare\per_lead.json`

| field | key(s) |
|---|---|
| `lead`, `models`, `main_set`, `declined_by_guard`, `rows`, `links.<m>` | `problems/<p>/lead`, `/models`, `/main_set`, `/declined_by_guard`, `/rows`, `/links/<m>` |
| `draws_sha256` | `problems/<p>/draws/sha256_per_lead` |
| `<L>.active` | `problems/<p>/levels/<L>/active_set/n_J/value` |
| `<L>.structural_zero` | `problems/<p>/levels/<L>/active_set/structural_zeros` |
| `<L>.nonzero_players.<m>` | `problems/<p>/levels/<L>/models/<m>/n_nonzero/value` (counted over J, line 333; no interval) |
| `<L>.kendall_w_main_set` `{value, ci[0], ci[1], finite_replicates}` | `problems/<p>/levels/<L>/per_problem/kendall_w/{value, ci_low, ci_high, n_finite}` |
| `<L>.mean_pairwise_spearman_main_set` (same form) | `problems/<p>/levels/<L>/per_problem/mean_pairwise_spearman/*` |
| `<L>.stability_under_region_resampling.<m>` | `problems/<p>/levels/<L>/per_problem/stability/<m>/value` (no interval) |
| `families.<v>` ("own history", "global indices", "local drivers", "context and calendar", "seasonal normal") | `problems/<p>/levels/variable/families/variable_family/<v>` = `own_history`, `global_indices`, `local_drivers`, `context_and_calendar`, `seasonal_normal` |
| (derived) the variables whose family is "global indices" | `problems/<p>/levels/variable/families/global_indices` |
| `nonzero_forecast_rows` keys | `problems/<p>/nonzero_forecast/models_covered` |
| `nonzero_forecast_rows.<m>.rows` | `problems/<p>/nonzero_forecast/models/<m>/rows_used` |
| `nonzero_forecast_rows.<m>.top10` `[[name, share], ...]` | `problems/<p>/nonzero_forecast/models/<m>/top10/{names, shares}` |
| (derived) every variable-level player of the problem (the set compare_shap.py's item-8 shares are taken over, lines 312-315) | `problems/<p>/nonzero_forecast/models/<m>/J` |
| (derived) `"variable"` | `problems/<p>/nonzero_forecast/models/<m>/level` |
| (derived) `len(main_set)`, `active` when the main set has two or more models, else null | `problems/<p>/levels/<L>/per_problem/kendall_w_m`, `kendall_w_n` |
| `<L>.players`, `regions`, `draws`, `salt`, `sample_sha256`, `global_columns`, `reference_link`, `j_rule`, `problem` | no key; checked: `players` = J + structural zeros; `regions` = the regions of the rows; `draws` = the matrix's rows; `salt` = `shap_v1|AW4|<p>|0`; `sample_sha256` = the registered sample; a variable is a global index exactly when all its `x__` columns are in `global_columns` (variable maps from the pieces' meta.json) |

### `compare\bootstrap_draws.npy`

| property | key |
|---|---|
| shape, dtype (as loaded) | `problems/<p>/draws/shape`, `/dtype` |
| SHA-256 of every byte of the file (computed by the reconciler) | `problems/<p>/draws/sha256_computed`; equality with per_lead.json: `/sha256_match` |
| (derived) the region order compare_shap.py uses: `sorted(set(group))` of its first model's `rows.parquet` (lines 146-148) | `problems/<p>/draws/regions_in_draw_order` |

### `compare\importance.parquet` (columns `level, model, player, active, mean_abs, share, signed_mean, sign_determined`)

| column | key |
|---|---|
| `player` where `active` (per level) | `problems/<p>/levels/<L>/active_set/J` |
| `mean_abs` | `problems/<p>/levels/<L>/models/<m>/players/<player>/I/value` |
| `share` | `.../players/<player>/share/value` |
| `signed_mean` | `.../players/<player>/signed_mean/value` |
| `sign_determined` | `.../players/<player>/sign_determined` |
| the active rows sorted by `share` descending, then `player` ascending, first ten (as the AW3 table, line 437) | `problems/<p>/levels/<L>/models/<m>/top10/{names, shares}` |
| (derived) the active rows sorted by `mean_abs` descending, then `player` ascending (compare_shap.py's `ST.ranked` over J) | `problems/<p>/levels/<L>/models/<m>/ranking` |
| (derived) per pair: the union of the two top-20 and of the two top-10 sets of those rankings; the players of the top-10 union with `sign_determined` true and a nonzero `signed_mean` in both models (shapv1_stats.py `sign_agreement`) | `.../pairs/<a\|b>/top20_union`, `/sign_union_top10`, `/sign_determined_both` |
| (derived) the mean of the main-set rivals' `share` per variable | `problems/<p>/main_row/consensus_shares/<v>`; with AW4_main_row.json's names: `main_row/consensus_top3/shares` |
| `share` of treeroute for AW4_main_row.json's `treeroute_top3` names | `problems/<p>/main_row/treeroute_top3/shares` |
| (derived, fire only) treeroute's first three of its ranking, with their shares | `problems/fire/main_row/treeroute_top3/{names, shares}` |

Rows of players outside J (`active` false) are mapped to the same `players/<player>/...` keys. A and B have no entry
for them (the spec's `players` holds the players of J), so they are numbers present only in the official source.

### `compare\families.parquet` (columns `model, family, mean_abs, share`)

| column | key |
|---|---|
| `share` | `problems/<p>/levels/variable/models/<m>/family_shares/<family key>/value` (no interval) |
| `share` of family "own history" of each main-set rival | `problems/<p>/main_row/own_history_share_per_rival/<rival>` |
| (derived, fire only) `share` of treeroute's "own history" | `problems/fire/main_row/own_history_share_treeroute/value` |
| `mean_abs` | no results.json key; kept as `problems/<p>/levels/variable/models/<m>/family_mean_abs/<family key>` (present only in the official source) |

### `compare\pairs.parquet` (columns `level, model_a, model_b, pair_label, statistic, value, ci_low, ci_high, finite_replicates, signs_compared`)

`problems/<p>/levels/<level>/pairs/<model_a>|<model_b>/...` (compare_shap.py's pairs are in the models' sorted order,
so `model_a|model_b` is the spec's pair key):

| field | key |
|---|---|
| `[model_a, model_b]` | `/models` |
| `pair_label` starting "same-link" / "cross-link" | `/link_class` = `same-link` / `cross-link` |
| "(not comparable in scale or rank)" in the label | `/cross_link_label` |
| "; raw model, declined by its guard: X" in the label | `/declined` = [X] (else []) |
| (derived) both models in per_lead.json's `main_set` | `/both_in_main_set` |
| statistic `spearman` | `/spearman_J/{value, ci_low, ci_high, n_finite}` (n_finite = `finite_replicates`) |
| `spearman_top20_union`, `kendall_tau_b`, `jaccard_top5`, `jaccard_top10`, `jaccard_top20` | the keys of the same names |
| `rbo_p0.9`, `rbo_p0.95` | `/rbo_p090`, `/rbo_p095` |
| `tvd` | `/tv_shares` |
| `tvd_family` (variable level only) | `/tv_family_shares` |
| `sign_agreement_top10` | `/sign_agreement/{value, ci_low, ci_high, n_finite}`: the file writes ci NaN and finite_replicates 0, so the official source holds ci null and n_finite 0 |
| `signs_compared` of `sign_agreement_top10` | `/sign_n_determined/value` (no interval) |
| (derived) `round(sign_agreement x signs_compared)`, 0 when no sign is compared | `/sign_n_agree/value` |
| `spearman_top20_union` value of the variable-level pair (treeroute, rival) | `problems/<p>/main_row/spearman_top20_union_per_rival/<rival>` |

### `compare\AW4_main_row.json`

| field | key |
|---|---|
| `level`, `models_in_main_set` | `problems/<p>/main_row/level`, `/main_set` |
| (derived) `main_set` without treeroute (line 348) | `/rivals` |
| `kendall_w` `{value, ci: [low, high, finite]}` | `/kendall_w/{value, ci_low, ci_high, n_finite}` |
| `treeroute_vs_same_link_rivals_median_spearman_top20_union` `{value, ci, range}` | `/spearman_top20_union_median/*`; `range[0]`, `range[1]` = `/spearman_top20_union_min/value`, `/spearman_top20_union_max/value` (no interval) |
| `rbo_vs_consensus_p0.9` | `/rbo_p090_vs_consensus/*` |
| `treeroute_top3` (names) | `/treeroute_top3/names` |
| `consensus_top3` (names) | `/consensus_top3/names` |
| `own_history_share_treeroute`, `own_history_share_median_rival` | the keys of the same names (`/*`) |
| `cross_link_models`, `declined_models`, `reference_link`, `ci_format`, `link_note`, `problem`, `lead` | no key; checked: `declined_models` = per_lead.json's `declined_by_guard`, `models_in_main_set` = its `main_set`, `kendall_w` = its variable-level W |

### `compare\bootstrap_stats.parquet` (columns `level, draw, pair, spearman, spearman_top20_union, rbo_p0.9, tvd`)

Per-draw values, not results.json keys. Each column of each (level, pair), in draw order 0-1999, is compared with A's
and B's per-draw arrays `levels/<L>/pairs/<pair>/{spearman_J, spearman_top20_union, rbo_p090, tv_shares}` in
`V\A\draws\<p>.npz` and `V\B\draws\<p>.npz` (same tolerance; NaN equals NaN).

### `compare\pairs.parquet.done.json`

No key. Checked: its `sha256` and `bytes` equal those of `pairs.parquet`; its `finished` time is used for the B1
independence check (every comparison was finished before the first B1 run started, 2026-11-15 23:06:16).

### `compare\AW3_table.md`, `compare\AW4_table.md` (rounded values: second check only)

Every rounded cell is compared with the unrounded official value written the same way (`%.2f`; shares `%.1f%%`) and
with A's and B's values written the same way: the pair cells (value and interval ends), "(n signs)", W and the mean
pairwise Spearman, the stability line, each top-10 line (names, shares and "(n nonzero)"), the family table, the
nonzero-forecast lines and the AW4 row. These never replace the unrounded files.

## 3. Item 9 (B1)

There is no official B1 output; every key under `b1/` is compared A with B only. The reconciler also reads, as run
records: each `treeroute_B1\meta.json` (`players_nonzero`, `variables_nonzero`, the eight status fields,
`tree_shap_seconds`), `rows.parquet.done.json` (`seconds`), the main `treeroute\meta.json` (`duplicates_merged`),
`SHAP\SAMPLE_REGISTER.txt`, the logs `SHAP\logs\tr_shap_<p>_lead0.log` (the numbers on the B1 set-up and "done in"
lines; no line is copied), and defo's two `rows.parquet` (to recompute the identity check).
