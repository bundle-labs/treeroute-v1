# Implementer B, round 14: choices and identifications

Written before any official number was seen (no compare output beyond `per_lead.json`'s structural keys and
`bootstrap_draws.npy` was opened; `compare_shap.py` and `shapv1_stats.py` were not opened). Short names: SHAP =
`D:\treeroute\analysis\shap_v1`, V = `SHAP\verify_v1`. "The protocol" = `SHAP\PROTOCOL.md`. Every choice below is
applied by the same code to the main comparison (items 1-8) and to B1 (item 9): the pair statistics, the model
blocks, the families and the intervals live in one module, `V\B\scripts\b_lib.py`, called by both
`b_compare.py` and `b_b1.py`.

## C01 Rows flagged by S-RESID

**Choice:** Flagged rows enter every statistic like any other row (no row is dropped). In fact no row of any piece is
flagged: `resid_flag` is false on all 1,000 rows of all 29 row files, and every `meta.json` has
`rows_flagged_resid` 0, so the choice changes no number.

**Why:** Section 5 defines the flag only as a stop rule ("a model with more than 1% flagged rows stops"); sections 8
and 10 define every statistic on the explained rows and say nothing about leaving flagged rows out.

**B1:** Same as the main pairs (the B1 pieces have no flagged row either).

## C02 Region weights

**Choice:** I_m(j) = (1/G) sum over regions r of [ (1/n_r) sum over the rows i of r of |phi_ij| ]: the mean over the
regions of the within-region mean, so each region weighs 1 in total and each of its n_r rows weighs 1/n_r. On a draw,
each of the G drawn regions (with repetition) weighs 1: a region drawn c times weighs c, and the value is
(1/G) sum_r c_r * (region mean of r). The full sample is the draw with c_r = 1 for every region.

**Why:** Section 8: "I_m(j): the region-weighted mean |phi_ij| (each region weighs 1)" and "A paired cluster
bootstrap over regions: B = 2,000 draws of regions with replacement". A cluster bootstrap resamples whole regions, so a
region drawn twice counts twice.

**B1:** Same as the main pairs.

## C03 The signed mean

**Choice:** S_m(j) has the same weighting as I_m(j), with phi_ij in place of |phi_ij|: (1/G) sum_r c_r * (mean of
phi_ij over the rows of region r).

**Why:** Section 8 lists "the signed mean S_m(j)" right after the region-weighted I_m(j) in the same list; the natural
reading is the same mean with the sign kept.

**B1:** Same as the main pairs.

## C04 The threshold of the active set

**Choice:** Player j is in J when, for at least one model m, I_m(j) > 1e-12 * sum_k I_m(k), with I_m the region-weighted
mean |phi| of C02 on the full sample and the sum over all of the model's players (its total mean |phi|). Strictly
greater: equality does not qualify. A model whose total is 0 gives no player to J. (Diagnostic: the plain row mean,
each row weighing 1/1000, gives the same J at both levels of all five problems; key `active_set.extra`.)

**Why:** Section 8: "The players to which some model gives more than 1e-12 of its total mean |phi|"; "more than" is
strict; I_m(j) is the protocol's "mean |phi|" of a player.

**B1:** Same rule applied to the two runs (section 10: "the players to which either run gives more than 1e-12 of its
total mean |phi| (section 8's rule, applied to these two runs)").

## C05 The models that form J

**Choice:** "Some model" ranges over every model of `per_lead.json` `models`: same-link and cross-link models, the
guard-declined fire ridge included. One J per problem and level serves every statistic of that level: every model's
I, s, S and ranking, every pair (same-link and cross-link), Kendall's W, the mean pairwise Spearman, the stability,
the main-text row and item 8. B1 never enters it.

**Why:** Section 8 defines "Active set J (per level)" once per level and then "Pairwise statistics, every pair, both
levels, on J"; the brief: "For each problem p and the models of per_lead.json key models ...: 1. Active set J". Section
10: B1 "enters no J of those models".

**B1:** B1's numbers use the pair's own J (section 10), formed by the same rule from the main run and the B1 run.

## C06 Players with no column in a model's row file; the structural zeros

**Choice:** A player (or variable) with no column in a model's `rows.parquet` has phi = 0 on every row for that model:
I = 0, S = 0, share 0. It is in that model's ranking (at the bottom, tied with the other zeros, ordered by name, C10)
and can fill its top-k sets by name order (coral's treeroute: no `normal`; NDVI's BARDL: 10 of 503 players, 4 of 117
variables). The `players` map of every model holds every player of J. The structural zeros are the players of the
union of all models' columns at that level that are not in J.

**Why:** Section 10: BARDL's "zeros elsewhere mean "not an input"" and "Its top-5, top-10 and top-20 sets follow name
order beyond its three variables at the variable level, and beyond its nine columns at the feature level (section 8's
tie rule)"; section 8: "The others are listed as structural zeros".

**B1:** Same as the main pairs (the two runs have the same columns).

## C07 Fixed at the full sample, or found again on each draw

**Choice:**
- J: fixed at the full sample (so the top-20 Jaccard's condition "J has 200 or more players" is read once, on the
  full-sample J). On a draw a player of J may have importance 0; it stays in J.
- The top-5, top-10 and top-20 sets, the union of the two top-20 sets and the union of the two top-10 sets: found
  again on each draw, from that draw's tie-broken rankings.
- The determined signs: fixed, one status per model and player, from the bootstrap interval of the signed mean over
  all 2,000 draws (C17). On each draw the signs compared are those of that draw's signed means.
- The consensus of the main row and its ranking: rebuilt per draw (section 8 says so).
- B1's pair J: fixed at the full sample, as J.

**Why:** Section 8: "The importances, every statistic and every number of the main-text row are recomputed per draw":
the top-k sets and their unions are parts of the statistics and are recomputed; J and the determined signs are the
definitions of the comparison's domain and of a sign being "determined" ("the bootstrap 95% interval of the signed
mean excludes 0" is a property of all the draws together, so it cannot be found again within one draw).

**B1:** Same as the main pairs.

## C08 Intervals for counts

**Choice:** `n_J` (and B1's pair `n_J`): no interval (J is fixed, C07; `ci_low`, `ci_high`, `n_finite` null with
why). `n_nonzero` (and B1's `n_nonzero`, `n_nonzero_before_merge`), `sign_n_determined` and `sign_n_agree`: an interval,
recomputed on each draw (percentile ends may then be non-integers, C21).

**Why:** Section 10 leaves "whether a count gets an interval" open; a count that is recomputed per draw ("every
statistic ... recomputed per draw") has a distribution, a fixed one does not.

**B1:** Same as the main pairs.

## C09 Nonzero players

**Choice:** A player is nonzero for model m when its importance is positive, I_m(j) > 0 (every row has a positive
weight, so this means phi_ij != 0 on at least one explained row), counted over all of the model's own columns (outside J
too). On a draw: the players with I*_m(j) > 0 on that draw. (Diagnostic: the full-sample count equals `meta.json`
`players_nonzero` / `variables_nonzero` for every piece, the B1 pieces included; key `models.<m>.extra.meta_nonzero`.)

**Why:** Section 8: "the number of nonzero players", listed with the importance vector; "nonzero" read literally on the
importance, without a threshold.

**B1:** Same; at the feature level also before any summing of merged context columns (no column needed summing).

## C10 Ties and name order

**Choice:** A tie is exact float64 equality of I_m(j) (no tolerance), read on I_m (the shares are I_m divided by one
number). Average ranks for Spearman and Kendall's W; tau-b counts exactly equal pairs as ties. In every ordered
ranking (the `ranking` lists, top-5/10/20 sets, RBO, the top-10 and top-3 lists, the consensus ranking), larger I comes
first and tied players are ordered by name ascending, the name being the player as written in the results (the
`phi__` column name without `phi__`, so with its `x__` / `c__` prefix; the variable name without `phiv__`), compared
by Python's default string order (Unicode code points, upper case before lower case). -0.0 ties with 0.0.

**Why:** Section 8: "Spearman's rho on average ranks", "Kendall's tau-b with the tie correction", "ties broken by name";
section 10: "Ties follow section 8's tie rule". No tolerance is stated, so equality is exact.

**B1:** Same as the main pairs.

## C11 Spearman's expression and the top-20 union

**Choice:** Spearman's rho = Pearson's correlation of the two average-rank vectors (not 1 - 6 sum d^2 / (n(n^2 - 1)),
which is wrong with ties); undefined (NaN) when either rank vector has zero variance. Over the union of the two top-20
sets: the union of the two models' top-20 sets (tie-broken rankings over J), and rho of their importances restricted
to the union, with the ranks taken again within the union (average ranks among the union's players).

**Why:** Section 8: "Spearman's rho on average ranks, over J and over the union of the two top-20 sets": the
correlation is computed over that set, so the ranks are those within that set.

**B1:** Same as the main pairs.

## C12 Size conditions of the top-k sets

**Choice:** When J has fewer than k players, the top-k set is all of J (Jaccard 1 if both are). The top-20 Jaccard is
computed only when the full-sample J of that level has 200 or more players (defo and NDVI feature level; NDVI's B1
feature-level pair J), else null with why. The top-20 and top-10 unions are always formed.

**Why:** Section 8: "Jaccard similarity of the top-5 and top-10 sets (and top-20 when J has 200 or more players)"; J
is fixed (C07), so the condition is read on it.

**B1:** Same, read on the pair's own J (section 10: "top-20 when J has 200 or more players", J = the pair's).

## C13 RBO's form

**Choice:** With both rankings full tie-broken permutations of J (length k = |J|) and X_d = |top-d(a) ∩ top-d(b)|:

RBO = ((1 - p) / p) * sum_{d=1}^{k} (X_d / d) * p^d + (X_k / k) * p^k,

for p = 0.9 and 0.95, with no other normalisation. This is eq. 32 of Webber, Moffat and Zobel (2010) (extrapolated RBO
for lists of lengths s <= l) with s = l = k: its second sum is empty and (X_l - X_s)/l vanishes. Here X_k = k, so the
last term is p^k; RBO of a ranking with itself is 1 (checked in `b_selftest.py`, with a direct evaluation of eq. 32 on
reversed and random permutations).

**Why:** Section 8: "RBO on the full rankings over J (equal length, ties broken by name; eq. 32 of Webber, Moffat and
Zobel 2010 reduces to its finite form), p = 0.9 and 0.95".

**B1:** Same as the main pairs.

## C14 Total-variation distance

**Choice:** TV = (1/2) * sum_{j in J} |s_a(j) - s_b(j)| with the shares over J (each sums to 1); between family shares:
(1/2) * sum over the five families of |F_a(f) - F_b(f)|.

**Why:** Section 8: "the total-variation distance between shares (feature or variable level) and between family
shares"; the factor 1/2 is the standard definition (distance in [0, 1]).

**B1:** Same, with the shares over the pair's J (section 10: "between the two runs' shares over this J").

## C15 Family attribution and family shares

**Choice:** A family's attribution on a row is the sum of the variable-level phi of all of the family's variables on
that row (those outside J are 0 or negligible). Its importance is the region-weighted mean (C02) of the absolute value
of that row sum; a family share is that importance divided by the sum of the five families' importances (so the five
shares sum to 1). A family with no variable in a problem (coral has no own-history variable; families with no
variable are listed in `families.extra`) has attribution 0 on every row and share 0, reported as the value 0 with its
interval [0, 0]. The feature-level pairs carry the same family-share distance as the variable-level pairs (families are
built from variable-level phi only); `family_shares` are reported at the variable level only.

**Why:** Section 8: "A family's attribution on a row is the sum of its variables' (variable-level) phi on that row";
section 14 (v3): "group attribution as a sum of phi per row (v2's code summed shares of mean |phi|)". The pairs carry a
family-share distance at "both levels", but family attribution is defined from variable-level phi, so there is one
family-share vector per model.

**B1:** Same (the B1 run's families from its variable-level phi, with items 1-3's families and global-index rule).

## C16 Family membership and the global-index rule

**Choice:** Precedence, in this order: `normal` -> seasonal normal; `hist_*` -> own history; `calendar` and `ctx:<name>`
-> context and calendar; then the global-index rule on the other variables -> global indices; the rest -> local
drivers. A column "takes one value per time step" when, on every time step of the lead's test set (the row's `time`,
which equals `issue` at lead 0), all of that step's test rows hold the same stored value (exact equality of the
float32 values), a missing value counting as a value of its own (all missing at a step passes; some missing fails).
The units compared at a step are those with a row at that step. A variable is a global index when every one of its
columns (every `x__` player mapped to it in any model's `variable_map`) passes; every such column is in the test set.
(Ignoring missing values instead gives the same global indices on all five problems.) Result: coral `nino34a`;
defo, fire and pm25 27 indices; NDVI 26 (list in `families.global_indices`).

**Why:** Section 8: "own history (`hist_*`), global indices (a variable all of whose columns take one value per time
step across every unit of the lead's test set), local drivers, context and calendar, the seasonal normal" and "context
columns are `calendar` (month and harmonics) or `ctx:<name>`": own history, context and the normal are named by their
columns, so they keep their family even though the month takes one value per time step; local drivers are the rest.

**B1:** Same families and global indices (section 10: "section 8's five families, with section 8's rule for global
indices").

## C17 Determined signs and sign agreement

**Choice:** A model's sign for player j is determined when the percentile 95% interval (C21) of S_m(j) over the 2,000
draws has ci_low > 0 or ci_high < 0 (strict: an end exactly 0, or a zero-width interval at 0, is not determined; S is
finite on every draw). Sign agreement = n_agree / n_determined: n_determined = the players of the union of the two
top-10 sets whose sign is determined in both models; n_agree = those of them with sign(S_a(j)) = sign(S_b(j)). When
n_determined is 0 the agreement is undefined (null with why on the full sample, NaN on a draw). On a draw: the union
of that draw's top-10 sets, the fixed determined status, the signs of that draw's S.

**Why:** Section 8: "sign agreement of S_m on the union of the two top-10 sets, among the players whose sign is
determined in both models (determined: the bootstrap 95% interval of the signed mean excludes 0), with that count."

**B1:** Same, determined in both runs.

## C18 Undefined statistics

**Choice:** Undefined (NaN on a draw, not counted in `n_finite`; null with why on the full sample): Spearman over J or
over the top-20 union when either rank vector has zero variance; Kendall's tau-b when either side is all tied; sign
agreement when no player is determined in both; Kendall's W when the main set has fewer than two models (fire: null
with why, as are `kendall_w_m` and `kendall_w_n`), or when every ranking is all tied; the mean pairwise Spearman when
the main set has no pair; every main-row number that needs a rival when there is none (fire); item 8 on a draw whose
drawn regions hold no row with pre > 0. Everything else always has a value.

**Why:** Section 8: "Percentile 95% intervals, each with its number of finite replicates"; the brief: "Fire's main set
is treeroute alone: W and the pair statistics are undefined there, and treeroute's top 3 and own-history share still
have values".

**B1:** Same as the main pairs.

## C19 Kendall's W and the mean pairwise Spearman

**Choice:** W over the main set's models (per_lead.json `main_set`), each ranking its importances over the level's
J (all of J, zeros included), with the tie correction W = 12 S / (m^2 (n^3 - n) - m sum_i T_i), T_i = sum over tie
groups of (t^3 - t), S = sum_j (R_j - m(n+1)/2)^2 on average ranks. It is computed as S / (m sum_i V_i) with V_i =
sum_j (r_ij - (n+1)/2)^2, which is the same number (checked against the textbook form on every full sample and in the
self-test). The mean pairwise Spearman is the mean of the Spearman correlations over J of the C(m, 2) main-set pairs.

**Why:** Section 8: "Kendall's W over the main set with the tie correction; the mean of the pairwise Spearman
correlations of the main set (computed directly ...)"; W and the identity (mW - 1)/(m - 1) both refer to Spearman over
the same players, J.

**B1:** Not applicable (B1 enters no W).

## C20 Stability

**Choice:** For model m and each draw b: rho_b = Spearman over the level's J between the full-sample I_m and the draw's
I*_m. The stability is the mean of the finite rho_b. It gets no interval (`ci_low`, `ci_high`, `n_finite` null with
why); the number of finite rho_b and their 2.5, 50 and 97.5 percentiles are in `per_problem.extra`.

**Why:** Section 8: "each model's stability under region resampling (the mean Spearman between its full-sample
importances and its own bootstrap replicates: descriptive, not a ceiling on between-model agreement)": it is a mean
over the replicates, so an interval for it would need a bootstrap within each draw.

**B1:** Not applicable (section 10 lists no stability for B1).

## C21 Percentile intervals

**Choice:** `numpy.percentile(values, [2.5, 97.5])` with numpy's default linear interpolation (Hyndman and Fan type 7)
over the finite replicates only; non-finite replicates are left out and `n_finite` counts the finite ones. An interval
is given whenever at least one draw is finite.

**Why:** Section 8: "Percentile 95% intervals, each with its number of finite replicates. BCa is not computed."

**B1:** Same as the main pairs.

## C22 The main row's median and range

**Choice:** The median over treeroute's same-link rivals (main set minus treeroute) of the variable-level top-20-union
Spearman; with an even number of rivals (NDVI, 4) the mean of the two middle values (`numpy.median`). Its interval:
the median recomputed on each draw from that draw's per-rival values. The range is reported as its two ends, the min
and the max over the rivals, each recomputed on each draw with its own interval.

**Why:** Section 8: "treeroute against its same-link rivals: the median of the top-20-union Spearman [CI] and the
range" and "every number of the main-text row are recomputed per draw".

**B1:** Not applicable (B1 is in no main row).

## C23 "The median rival"

**Choice:** The median of the rivals' own-history shares (C24), recomputed per draw; with an even number of rivals the
mean of the two middle values. `median_rival_name` names a rival only when the number of rivals is odd and exactly one
rival has the median value on the full sample (defo, pm25: one rival); otherwise null with why (NDVI: four rivals;
coral: all three rivals have share 0).

**Why:** Section 8: "the own-history share of treeroute [CI] and of the median rival [CI]": read as the median of the
rivals' values; a rule picking one rival by another statistic is not given.

**B1:** Not applicable.

## C24 The own-history share

**Choice:** The own-history family's share of C15 (the region-weighted mean of |sum of the `hist_*` variables' phi| on a
row, divided by the sum of the five families' importances), with its interval.

**Why:** Section 8 lists the families "for shares", own history first; section 10 (B1): "its family shares ..., its
top 3 variables and its own-history share".

**B1:** Same (the B1 run's own-history family share).

## C25 Arcsine models' nonzero forecasts (item 8)

**Choice:** Every arcsine-link model (per_lead.json `links`) of every problem: coral's rival_hgb_l1, rival_lgbm,
rival_rf and treeroute; fire's treeroute. For each, its own rows with pre > 0 (its own `pre` column). On those rows, at
the variable level: I, share, signed mean and sign_determined, the number of nonzero variables, the ranking and the
top-10, over the problem's variable-level J (C05). Region weighting: each region with at least one such row weighs 1
(a region without such rows drops out); on a draw each drawn copy of such a region weighs 1, and a draw that holds none
gives NaN. Intervals from the same draws.

**Why:** Section 8: "For every arcsine-link model, the variable-level importances on its rows with a nonzero forecast
(pre > 0) are also reported (fire)"; "(fire)" read as the case that motivates it (section 5), not as a limit.

**B1:** Not computed for B1 (section 10: "Fire's view on its rows with a nonzero forecast ... is not computed for B1").

## I01 The region of a row

**Choice (identification):** The region is the `group` column of `rows.parquet` (section 9: rows.parquet holds "keys,
region, ..."; no column is named `region`, and `group` is the engine's region). Every piece of a problem has the same
(`row`, `group`) on its 1,000 rows. The number of distinct groups equals the draw matrix's column count (coral 37,
defo 42, fire 40, pm25 127, NDVI 133) and, except coral, equals the export manifest's `groups` list.

**Why:** Section 9 and the data (`rows.parquet` of every piece).

**B1:** Same (the B1 pieces have the same `row` and `group` as the main runs).

## I02 The draw matrix

**Choice (identification):** Row b of `bootstrap_draws.npy` (b = 0..1999) is draw b; its G columns are the G regions
drawn with replacement; each value is an index into the problem's regions in ascending order (Python `sorted()` of the
distinct `group` values of the sample's rows). The matrix is reproduced exactly, every row and column of all five
problems, by value[b, k] = int.from_bytes(SHA-256("shap_v1|AW4|<problem>|0|<b>|<k>")[:8], "big") mod G (the protocol's
"SHA-256 generator with the salt `shap_v1|AW4|<problem>|<lead>`"; checked in `b_selftest.py` and `b_compare.py`). The
values lie in [0, G - 1]. The generator yields indices only: which region an index names is not recorded in any file
this round may read, so the ascending order is my identification. It is also the order in which the regions first
appear in every piece's rows sorted by `row` and in `SHAP\sample\<p>\sample.parquet` (the sample's rows are grouped by
region in ascending order, on all five problems), and for defo, fire, pm25 and NDVI the order of the export manifest's
`groups`; so the two natural orders (sorted, first appearance) give the same list. The npz rows follow the draw order
of the matrix.

**Why:** Section 8: "B = 2,000 draws of regions with replacement, the same draws for every model. The draw matrix comes
from the SHA-256 generator with the salt `shap_v1|AW4|<problem>|<lead>` and is saved with its SHA-256."

**B1:** The same draws (section 10).

## I03 The draws' SHA-256

**Choice (identification):** The SHA-256 of every byte of the `.npy` file as saved (header and data, read in binary)
equals `per_lead.json` `draws_sha256` on all five problems. (The SHA-256 of the array's data bytes alone differs.)

**Why:** Section 9: "`bootstrap_draws.npy` (SHA-256 in `per_lead.json`)".

**B1:** The same check, made again by `b_b1.py` (`run.draws_sha256_match`).

## I04 The lead's test set

**Choice (identification):** The lead's test set is the test part of the rivals' export of the headline run, lead 0:
`D:\treeroute\rival_export\<problem>\<run>\lead_0\test\*.parquet` (one file per region; coral 20261020_f3b8e3da,
defo 20261017_d71c61f4, fire 20261017_869d1f38, pm25 20261007_74e67609, NDVI 20261016_d1de3158). Its row count equals
`export_manifest.json` `counts.test` (coral 2,312, defo 369,096, fire 96,000, pm25 91,440, NDVI 95,184), the rows the
rivals' S-EXACT checks reproduce ("every test row"). Read: `unit`, `time`, `issue` and the `x__` columns of the
candidate variables only (`families.test_set_columns`); from the manifest only `counts` and `groups`.

**Why:** The brief: "'Global indices' needs the lead's test set (section 8's rule): find it from the run's records, read
only the columns you need." The export is the run's record of the test rows with their input columns (the same column
names as the players); the protocol names no other file that holds the test set's inputs.

**B1:** Same.

## I05 The registered sample SHA-256

**Choice (identification):** In `SHAP\SAMPLE_REGISTER.txt`, the one line of the problem (its `leads=` include 0): its
`sample=` field, the SHA-256 of `sample.parquet` (the sample is lead-invariant, section 3). Each B1 `meta.json`
`sample_sha256` equals it (defo, fire, pm25, NDVI).

**Why:** The brief: "`sample_sha256` (it must be the registered one, `SHAP\SAMPLE_REGISTER.txt`)".

**B1:** This identification is for B1.

## I06 The B1 lines of the logs

**Choice (identification):** A line's writing time is the bracketed time at its start (`[YYYY-MM-DD HH:MM:SS + ...s]`).
The B1 lines are those with a time at or after 2026-11-15 23:06:00. The set-up line is the first of them containing
"<n> rows, <pairs> background pairs" (pairs = that number); the "done in" line is the first after it containing
"done in <total> s (tree SHAP <tree> s)" (total seconds and tree-SHAP seconds). Each log has exactly one of each:
defo lines 24 and 30, fire 20 and 26, pm25 25 and 39, NDVI 17 and 32 (fire's earlier B1 lines of the smoke world,
2026-11-12, fall before the time and are not used).

**Why:** The brief: "the B1 lines are those written from 2026-11-15 23:06"; item 9: "from its log's set-up line and
"done in" line".

**B1:** This identification is for B1.

## X01 Which `pre` defines an arcsine model's nonzero rows

**Choice:** Each model's own `pre` column (its own forecast in y units), not treeroute's.

**Why:** Section 8: "the variable-level importances on its rows with a nonzero forecast (pre > 0)": "its" forecast.

**B1:** Not applicable.

## X02 Precedence of the family rules

**Choice:** As in C16: the families named by their columns (seasonal normal, own history, context and calendar) come
before the global-index test; `calendar` takes one value per time step but stays in context and calendar.

**Why:** Section 8 names those three families by their columns; the global-index rule describes driver inputs.

**B1:** Same.

## X03 The feature-level family-share distance

**Choice:** The feature-level pairs' `tv_family_shares` is the same number (and the same per-draw values) as the
variable-level pairs': family shares come from variable-level phi only.

**Why:** Section 8: "A family's attribution on a row is the sum of its variables' (variable-level) phi".

**B1:** Same.

## X04 The main row's Kendall's W

**Choice:** `main_row.kendall_w` is the variable-level Kendall's W of item 5 over the main set, computed again from the
same rankings (it equals `levels.variable.per_problem.kendall_w`).

**Why:** Section 8's main-text row: "Kendall's W [CI]" at the variable level.

**B1:** Not applicable.

## X05 Shares when a draw drops every row of a player

**Choice:** Shares on a draw are over J with that draw's importances; a player of J whose nonzero rows are all in
undrawn regions has importance and share 0 on that draw and ranks with the zeros (ties by name).

**Why:** Follows from C02 and C07 (J fixed, importances recomputed).

**B1:** Same.
