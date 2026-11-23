# Implementer A, round 14: open choices and identifications

Written from the protocol's words (`SHAP\PROTOCOL.md` sections 5, 8, 9 and 10), the brief and the spec, before any
official number was seen. No official output was opened: not `compare_shap.py`, not `shapv1_stats.py`, no compare
file except `per_lead.json` (structural keys only) and `bootstrap_draws.npy`. The one-line form of each entry is in
`results.json` key `choices`. Names: SHAP = `D:\treeroute\analysis\shap_v1`, V = `SHAP\verify_v1`.

One code path (`scripts\a_core.py`) computes the main pairs and the B1 pair, so every choice below is made the same
way for B1 unless the entry says otherwise.

## C01 Rows flagged by S-RESID

**Choice:** every row enters every statistic. No row of any piece is flagged: `resid_flag` is false on all 1,000 rows
of all 29 row files (B1 pieces included; also `rows_flagged_resid` = 0 in every `meta.json`), so this choice changes
no number.

**Why:** sections 8 and 10 define the statistics over the explained rows and name no exclusion; section 5 only says a
row "is flagged" and "a model with more than 1% flagged rows stops".

**B1:** same as the main pairs.

## C02 Region weights

**Choice:** I_m(j) = (1/G) sum over regions r of (mean over the rows i of r of |phi_ij|): the rows of a region are
averaged, then the G regions are averaged with weight 1 each. On a draw, a region drawn k times enters k times:
I*(j) = sum_r (k_r / G) x (the region-r mean), k_r its count among the draw's G picks.

**Why:** "I_m(j): the region-weighted mean |phi_ij| (each region weighs 1)"; "A paired cluster bootstrap over
regions: B = 2,000 draws of regions with replacement" (a cluster bootstrap resamples whole regions; each copy keeps
its weight 1).

**B1:** same as the main pairs.

## C03 The signed mean

**Choice:** S_m(j) is weighted exactly as I_m(j): region means of the signed phi_ij, each region weighing 1 (on a
draw, by its count).

**Why:** "I_m(j): the region-weighted mean |phi_ij| (each region weighs 1); shares s_m(j) = I_m(j) / sum over J; the
signed mean S_m(j)": one sentence, one weighting.

**B1:** same as the main pairs.

## C04 The threshold of the active set

**Choice:** j is in J when, for some model m, I_m(j) > 1e-12 x T_m, where T_m is the sum of I_m over all of m's
players (a player m has no column for counts 0) and I is the region-weighted mean |phi| of C02. The comparison is
strict, so equality stays out. A model whose total is 0 adds no player.

**Why:** "The players to which some model gives more than 1e-12 of its total mean |phi|": "mean |phi|" is section 8's
importance I_m, "its total" the model's sum over its players, "more than" a strict comparison.

**B1:** the same rule on the two runs (section 10: "section 8's rule, applied to these two runs").

## C05 The models that form J

**Choice:** "some model" ranges over every model of per_lead.json's `models`, cross-link and guard-declined models
included (fire's declined rival_ridge counts). One J per level serves every statistic of the problem: the pairs,
W, the mean pairwise Spearman, the stability, the main row and item 8.

**Why:** section 8 defines a single "Active set J (per level)" for the problem-lead and then computes "Pairwise
statistics, every pair, both levels, on J"; the pairs include cross-link and declined models.

**B1:** the pair's J comes from the two runs only (section 10); B1 enters no J of items 1-8.

## C06 Players with no column in a model's row file; the structural zeros

**Choice:** a player (or variable) with no column in a model's file has phi = 0 on every row for that model: I = 0,
S = 0, share 0. It enters the model's ranking and top-k sets as a 0, tied with the model's other zeros and ordered by
name. Each model's `players` map has an entry for every player of J. The structural zeros are the names of the union
of all models' columns (per level) that are not in J. Found: coral `normal` (both levels: the rivals' phi__normal is
0 on every row, and treeroute has no normal); fire, pm25, ndvi and defo: `normal`, the static columns and (where they
exist) the context columns, as section 5 expects under B2.

**Why:** section 10 on BARDL: "Its zeros elsewhere mean 'not an input'. ... Its top-5, top-10 and top-20 sets follow
name order beyond its three variables at the variable level, and beyond its nine columns at the feature level
(section 8's tie rule)"; section 5: the neighbour kind (coral treeroute) has "no normal".

**B1:** same as the main pairs (the two runs have the same columns).

## C07 Fixed at the full sample, or found again on each draw

**Choice:**
- J, and with it the top-20 Jaccard's condition "J has 200 or more players": fixed at the full sample. B1's pair J:
  fixed at the full sample.
- The top-5, top-10 and top-20 sets, the union of the two top-20 sets and the union of the two top-10 sets: found
  again on each draw, from that draw's importances.
- The determined signs: fixed. They are defined by the bootstrap interval over all draws. On a draw, the sign
  agreement uses that draw's top-10 union, the fixed determined set and that draw's signed means.

**Why:** J sorts the "structural zeros" from the active players. It is a property of the sample, and "Pairwise
statistics ... on J" fixes the domain. "The importances, every statistic and every number of the main-text row are
recomputed per draw" means the top-k sets follow each draw's importances: a fixed top-k set would make the Jaccard
the same on every draw. "Determined: the bootstrap 95% interval of the signed mean excludes 0" is a property of the
whole bootstrap and cannot be found again within one draw. For the reconciler: had J been found again per draw, its
size would vary (`active_set.extra.n_J_if_recomputed_per_draw`): coral 68/25 and fire 111/94 always, defo feature
278-280, pm25 101-103 (feature) and 87-89 (variable), ndvi 477-479 and 94-96.

**B1:** same as the main pairs.

## C08 Intervals for counts

**Choice:** a count that is recomputed on each draw gets an interval: `n_nonzero` (and B1's
`n_nonzero_before_merge`), `sign_n_determined` and `sign_n_agree`. `n_J` and B1's pair `n_J` have none, because J is
fixed (C07).

**Why:** "every statistic ... recomputed per draw. Percentile 95% intervals, each with its number of finite
replicates."

**B1:** same as the main pairs.

## C09 Nonzero players

**Choice:** a player is nonzero when I_m(j) > 0 exactly (some row has phi_ij != 0). The count is taken over the
model's own columns, not only J. On a draw the same test is applied to that draw's I. This reproduces every piece's
`meta.json` count (`players_nonzero`, `variables_nonzero`) on the full sample, B1 included (fire 113/96, pm25 105/91,
ndvi 482/96).

**Why:** "the number of nonzero players": a player whose attribution is not zero.

**B1:** same as the main pairs. At the feature level the count is reported after and before the merge step. They are
equal because no column needed summing.

## C10 Ties and name order

**Choice:** a tie is exact float64 equality of I_m(j), with no tolerance. Ranks are read on I_m: a model's shares are
I_m over one positive number and keep the same order. "Name" is the player or variable name as written in the results
(no `phi__`/`phiv__` prefix; `x__` and `c__` kept), compared in ascending Python string order (code point). One
strict order (I descending, then name ascending) gives each model's ranking, its top-5/10/20 sets, RBO's rankings and
the top-10 and top-3 lists (the consensus is ordered the same way). Spearman, tau-b and W use average ranks with
exact ties.

**Why:** "Spearman's rho on average ranks"; "Kendall's tau-b with the tie correction"; "Jaccard similarity of the
top-5 and top-10 sets (...), ties broken by name"; "RBO on the full rankings over J (equal length, ties broken by
name ...)"; section 10: "Ties follow section 8's tie rule."

**B1:** same as the main pairs.

## C11 Spearman's expression and the top-20 union

**Choice:** rho is the Pearson correlation of the two average-rank vectors (it equals `scipy.stats.spearmanr` on
tied toy data; self-test). Over the union of the two top-20 sets (each set by C10's strict order), the two models'
I values on the union are ranked again within the union (average ranks) and then correlated. For the reconciler,
`pairs.<a|b>.extra.spearman_top20_union_ranks_carried_from_J` gives the full-sample value with ranks carried from J.

**Why:** "Spearman's rho on average ranks, over J and over the union of the two top-20 sets": the union is the set
the statistic is computed over.

**B1:** same as the main pairs.

## C12 Size conditions of the top-k sets

**Choice:** a top-k set holds min(k, |J|) names. Every J here has more than 20 players, so every set is full. The
top-20 Jaccard is computed only when the full-sample J of that level has 200 or more players (B1: the pair's J).
That holds for defo and ndvi at the feature level (280 and 479) and for ndvi's B1 feature level (482). Otherwise the
key is null with its why.

**Why:** "Jaccard similarity of the top-5 and top-10 sets (and top-20 when J has 200 or more players)".

**B1:** the same rule, read on the pair's J (section 10: "top-20 when J has 200 or more players").

## C13 RBO's form

**Choice:** RBO(S, T, p) = (1 - p) x sum_{d=1..n} p^(d-1) A_d + p^n x A_n, where A_d = |S_{1:d} intersect T_{1:d}| / d,
n = |J|, and S and T are the two full strict rankings of J (C10). This is eq. 32 (RBO_ext) with s = l = n: its second
sum is then empty, and its last term ((X_l - X_s)/l + X_s/s) p^l becomes (X_n/n) p^n. For two permutations of J,
A_n = 1. No other normalisation is applied. In the self-test the RBO of a ranking with itself is 1 to within one ulp
(for example 0.9999999999999999 at n = 37, p = 0.9), and the code equals a direct prefix-set computation.

**Why:** "RBO on the full rankings over J (equal length, ties broken by name; eq. 32 of Webber, Moffat and Zobel
2010 reduces to its finite form), p = 0.9 and 0.95".

**B1:** same as the main pairs.

## C14 Total-variation distance

**Choice:** TV = 1/2 x sum_{j in J} |s_a(j) - s_b(j)|, on the two models' shares over J. The family TV is
1/2 x sum_f |F_a(f) - F_b(f)| over the families the problem has (C15).

**Why:** "the total-variation distance between shares (feature or variable level) and between family shares": the
usual TV distance between two distributions (shares and family shares each sum to 1).

**B1:** same, over the pair's J ("between the two runs' shares over this J").

## C15 Family attribution and family shares

**Choice:**
- A family's attribution on a row is the sum of all of its variables' `phiv__` values on that row: every variable of
  the model's file in that family, not only those in J.
- A family's importance is the region-weighted mean of |that sum| (C02). The family share is that importance over the
  sum of the five families' importances.
- A family with no variable in the problem has a null share with its why: coral has no own-history variable, and
  defo has no calendar or context variable.
- Family shares exist at the variable level only. The feature-level pairs carry `tv_family_shares` null with its why,
  and the feature-level models carry no `family_shares`. For the reconciler, no feature-phi family numbers were
  computed.

**Why:** "Families, for shares: ... A family's attribution on a row is the sum of its variables' (variable-level) phi
on that row" (the words fix the variable-level phi); the change log: "group attribution as a sum of phi per row (v2's
code summed shares of mean |phi|)".

**B1:** same. B1's family shares and the pair's family TV are at the variable level; at the feature level
`tv_family_shares` is null with the same why.

## C16 Family membership and the global-index rule

**Choice:**
- Order of precedence: `hist_*` gives own history; `normal` gives the seasonal normal; `calendar` or `ctx:*` gives
  context and calendar. Then comes the data rule for global indices, and every other variable is a local driver.
- The rule: every column of the variable takes exactly one stored value at each `time` across all the units of the
  lead-0 test set present at that time. Equality is exact (float32 values, no tolerance). A time step where every unit
  is missing counts as one value (ndvi's `x__epo_lag12` has one). A step that mixes missing and present values fails.
  A column missing from the test set would fail (none is missing). `normal` is no test-set column.
- Result: coral `nino34a`. Defo, fire and pm25 have 27 global indices: amo, ao, epo, iod, nao, nino12, nino3, nino34,
  nino4, noi, oni, pdo, pna, sam, soi, the eight sst_anom_* indices, tna, tni, tsa and wp. Ndvi has 26: the same
  without sst_anom_mediterranean, which ndvi does not have.
- `calendar` also passes the rule (coral, fire, pm25, ndvi) but stays in context and calendar, which section 8 names
  explicitly.
- No column fails by a small spread only: none fails with a relative spread below 1e-5, so a tolerance would change
  nothing. Coral's units are visits and its time key is the visit date.

**Why:** "own history (`hist_*`), global indices (a variable all of whose columns take one value per time step across
every unit of the lead's test set), local drivers, context and calendar, the seasonal normal"; "context columns are
`calendar` (month and harmonics) or `ctx:<name>`".

**B1:** the same family map (brief: "the families and the global-index rule of items 1-3").

## C17 Determined signs and sign agreement

**Choice:** a sign is determined when the percentile 95% interval of S_m(j) over the finite draws (C21) has
ci_low > 0 or ci_high < 0, strictly. An end exactly at 0, or a zero-width interval at 0 (a name with no column), is not
determined. S is finite on every draw here (n = 2000). The reported `sign_agreement` is the fraction
n_agree / n_determined:
- n_determined is the number of players of the union of the two top-10 sets whose sign is determined in both models;
- n_agree is the number of those whose two signed means have the same sign (numpy sign).

When n_determined = 0 the agreement is undefined: null on the full sample, NaN on a draw. On a draw the statistic uses
that draw's top-10 union and signed means with the fixed determined set (C07).

**Why:** "sign agreement of S_m on the union of the two top-10 sets, among the players whose sign is determined in
both models (determined: the bootstrap 95% interval of the signed mean excludes 0), with that count."

**B1:** same as the main pairs.

## C18 Undefined statistics

**Choice:** these cases are undefined (null on the full sample with a why; NaN, so not finite, on a draw):
- Spearman, tau-b or W when a ranking is all ties (zero variance or a zero denominator);
- a sign agreement with no player determined in both models;
- a share or family share whose total is 0;
- W and the mean pairwise Spearman when the main set has fewer than 2 models (fire);
- every main-row number that needs a rival when there is none (fire);
- the own-history numbers of a problem with no `hist_*` variable (coral).

Every other statistic has a value. Cases met: fire's feature-level sign agreement of every pair with treeroute (no
player is determined in both), fire's variable-level `rival_ridge|treeroute` sign agreement, fire's W and main row,
and coral's own-history numbers.

**Why:** brief item 7: "Fire's main set is treeroute alone: W and the pair statistics are undefined there"; section
8: "Percentile 95% intervals, each with its number of finite replicates."

**B1:** same as the main pairs (no B1 number is undefined).

## C19 Kendall's W and the mean pairwise Spearman

**Choice:** both are taken over J of the level and the main set's models (m = |main_set|, n = |J|).
W = 12 S / (m^2 (n^3 - n) - m x sum_i T_i), where:
- S = sum_j (R_j - m(n+1)/2)^2;
- R_j is the sum of player j's average ranks;
- T_i = sum over rater i's tie groups g of (t_g^3 - t_g).

The mean pairwise Spearman is the mean of the m(m-1)/2 Spearman correlations over J (C11), computed directly. W is
checked by the self-test (no ties: (mW - 1)/(m - 1) equals the mean pairwise Spearman; identical tied rankings give 1;
a 3 x 6 textbook case) and against a direct loop on ndvi.

**Why:** "Kendall's W over the main set with the tie correction; the mean of the pairwise Spearman correlations of the
main set (computed directly: (mW - 1)/(m - 1) is exact only when every ranking has the same ties)".

**B1:** not used (B1 enters no W).

## C20 Stability

**Choice:** for each model, rho_b is the Spearman over J between its full-sample I and its I on draw b. The stability
is the mean of the finite rho_b. It has no interval, because it is itself a summary over the draws. The number of
finite rho_b and their 2.5% and 97.5% points are in `per_problem.extra.stability_per_draw_spearman`.

**Why:** "each model's stability under region resampling (the mean Spearman between its full-sample importances and
its own bootstrap replicates: descriptive, not a ceiling on between-model agreement)".

**B1:** not in section 10's B1 list, so not computed.

## C21 Percentile intervals

**Choice:** ci_low and ci_high are `numpy.percentile` of the finite replicates at 2.5 and 97.5, with numpy's default
linear interpolation (Hyndman-Fan type 7). Non-finite replicates are dropped first and the rest counted (`n_finite`).
An interval is given whenever n_finite >= 1; with 0 finite draws both ends are null with a why.

**Why:** "Percentile 95% intervals, each with its number of finite replicates. BCa is not computed."

**B1:** same as the main pairs.

## C22 The main row's median and range

**Choice:**
- The rivals are the main set without treeroute: the same-link, guard-passing rivals that per_lead.json's
  `main_set` already holds.
- The median is the numpy median of treeroute's top-20-union Spearman against each rival (variable level). For an
  even count it is the mean of the two middle values (ndvi has 4 rivals).
- Its interval is the percentiles of the per-draw medians of the per-draw values.
- The range reports its two ends, the min and the max over the rivals, each with its own interval from the per-draw
  min and max.

**Why:** "treeroute against its same-link rivals: the median of the top-20-union Spearman [CI] and the range";
"every number of the main-text row are recomputed per draw".

**B1:** not used.

## C23 "The median rival"

**Choice:** the median of the rivals' own-history shares (numpy median; for an even count, the mean of the two middle
values), recomputed on each draw. `median_rival_name` names the rival whose full-sample share is that median when the
count is odd. With an even count it is null with its why.

**Why:** "the own-history share of treeroute [CI] and of the median rival [CI]", read with "every number of the
main-text row are recomputed per draw".

**B1:** not used.

## C24 The own-history share

**Choice:** the own-history family's share (C15): the region-weighted mean of |the sum of the `hist_*` variables'
phiv| on each row, over the sum of the five families' importances. It is not the sum of the `hist_*` variables'
shares s_m(j).

**Why:** "Families, for shares: own history (`hist_*`) ... A family's attribution on a row is the sum of its variables'
(variable-level) phi on that row"; v3 replaced v2's "summed shares of mean |phi|" with "a sum of phi per row".

**B1:** same (B1's own-history share is its own-history family share).

## C25 Arcsine models' nonzero forecasts (item 8)

**Choice:**
- Models covered: every model of every problem whose link string starts with `arcsine`. That is coral's
  rival_hgb_l1, rival_lgbm, rival_rf and treeroute, and fire's treeroute.
- Rows: those where the model's own `pre` > 0. Coral: 983, 995, 1,000 and 973 rows in all 37 regions. Fire: 226 rows
  in 27 of 40 regions.
- Numbers, at the variable level: I, share and S with intervals; sign_determined; `n_nonzero` with an interval; the
  ranking and the top-10. Shares are taken over the problem's variable-level J.
- Weighting: each region with at least one such row weighs 1 (its such rows averaged), and regions without one drop
  out. On a draw a region weighs its count. A draw holding no such region would give non-finite values; none
  occurred.

**Why:** "For every arcsine-link model, the variable-level importances on its rows with a nonzero forecast (pre > 0)
are also reported (fire)"; section 5: "the comparison also reports each arcsine model's importances on its rows with
a nonzero forecast". I read "(fire)" as where the view matters most, not as a limit, because the rule says "every
arcsine-link model".

**B1:** not computed (brief: "in particular not item 8").

## I01 The region of a row

**Found:** the region is `rows.parquet` column `group`. It is identical, row for row, in every piece of a problem (B1
pieces included). Its number of distinct values equals the draw matrix's columns: coral 37, defo 42, fire 40,
pm25 127, ndvi 133. The test export's per-region files carry the same names.

**Why:** section 9: "rows.parquet: keys, region, ..."; no column is named `region`, and `group` is the only key with
G values.

**B1:** same (the B1 row files have the same `group` column).

## I02 The draw matrix

**Found:** `bootstrap_draws.npy` is int64 with shape (2000, G) and values 0..G-1. Row b is draw b. Its G entries are
the regions drawn with replacement, and a region may repeat: a draw holds 17-30 distinct coral regions of 37, and
70-92 distinct pm25 regions of 127.

The whole matrix of every problem is reproduced exactly (`scripts\a50_draws_generator_probe.py`; 2000 x G entries,
all five problems) by entry(b, k) = int.from_bytes(SHA-256(`shap_v1|AW4|<p>|0|<b>|<k>`)[:8], big-endian) mod G. That
is section 8's salt followed by the draw b and the pick k. The integers therefore do not depend on the region names.

I read them as indices into the problem's regions in Python `sorted()` order of `group`. In every problem that order
equals the regions' order of first appearance by `row`, so the two natural readings agree. The per-draw files keep
the matrix's row order: row b of every `.npz` array is draw b.

**Why:** section 8: "B = 2,000 draws of regions with replacement, the same draws for every model".

**B1:** the same matrix and the same region order for both runs.

## I03 The draws' SHA-256

**Found:** per_lead.json's `draws_sha256` is the SHA-256 of every byte of the `.npy` file as stored (its header and
its data). It matches for all five problems. The SHA-256 of the array's data bytes alone does not match.

**Why:** section 9: "bootstrap_draws.npy (SHA-256 in per_lead.json)".

**B1:** the same check (`b1.<p>.run.draws_sha256_match`).

## I04 The lead's test set

**Found:** the "test set:" line of `SHAP\logs\rival_shap_<p>_lead0.log` names the lead-0 test set that the rival SHAP
step read. It is `D:\treeroute\rival_export\<p>\<run>\lead_0` (coral 20261020_f3b8e3da, defo 20261017_d71c61f4, fire
20261017_869d1f38, pm25 20261007_74e67609, ndvi 20261016_d1de3158). The run's test rows are in `lead_0\test\`, one
parquet per region:

| problem | rows | units | time steps |
|---|---|---|---|
| coral | 2,312 | 2,312 visits | 793 dates |
| defo | 369,096 | 92,274 | 4 |
| fire | 96,000 | 2,000 | 48 |
| pm25 | 91,440 | 1,905 | 48 |
| ndvi | 95,184 | 1,983 | 48 |

Only `unit`, `time` and the feature columns of the problem's players (every `x__`/`c__` name in the pieces'
variable maps) were read. The export's names equal the players' names.

**Why:** brief item 3: "'Global indices' needs the lead's test set (section 8's rule): find it from the run's
records, read only the columns you need."

**B1:** same.

## I05 The registered sample SHA-256

**Found:** `SHAP\SAMPLE_REGISTER.txt` has one line per problem (`problem=<p>`, its `leads=` include 0), and its field
`sample=` is the registered hash. Every B1 piece's `meta.json` `sample_sha256` equals it: defo 9989bd58, fire
1edbc3d1, pm25 ccb17021, ndvi f2bb2a79.

**Why:** brief item 9: "sample_sha256 (it must be the registered one, SHAP\SAMPLE_REGISTER.txt)".

**B1:** this is a B1 identification.

## I06 The B1 lines of the logs

**Found:**
- Each line of `SHAP\logs\tr_shap_<p>_lead0.log` starts with `[YYYY-MM-DD HH:MM:SS + elapsed s]`. That stamp is the
  line's writing time.
- A B1 line is one stamped 2026-11-15 23:06 or later.
- The set-up line is the first B1 line containing "background pairs". The pairs are the integer before
  "background pairs".
- The "done in" line is the B1 line containing "done in". The total seconds are the number after "done in", and the
  tree-SHAP seconds the number inside "(tree SHAP ... s)".

Lines found (each log holds exactly one such pair; numbers given as set-up, done):

| problem | set-up line | done line | pairs | total s | tree-SHAP s |
|---|---|---|---|---|---|
| defo | 24 | 30 | 16,000 | 465.9 | 464.3 |
| fire | 20 | 26 | 187,186 | 2,636.6 | 2,631.6 |
| pm25 | 25 | 39 | 203,963 | 17,890.4 | 17,883.2 |
| ndvi | 17 | 32 | 201,768 | 11,883.1 | 11,871.8 |

Each equals `meta.json` (`pairs`, `tree_shap_seconds`) and `rows.parquet.done.json` (`seconds`).

**Why:** brief: "the B1 lines are those written from 2026-11-15 23:06"; item 9: "from its log's set-up line and 'done
in' line".

**B1:** this is a B1 identification.

## X01 Same-link test

**Choice:** a pair is same-link when the two per_lead.json `links` strings are equal. Each string holds the link, c
and ub.

**Why:** "A pair is same-link when both models explain in the same link space (same link, c and ub), else
cross-link."

**B1:** not used (the B1 pair is one model's two runs).

## X02 Non-finite inputs of per-draw aggregates

**Choice:** a per-draw aggregate (the median, min and max over the rivals, the consensus, the mean pairwise Spearman)
is non-finite on a draw when any of its inputs is. This did not occur.

**Why:** the protocol counts finite replicates per number; an aggregate of a missing value is missing.

**B1:** no aggregate is used.

## X03 The consensus

**Choice:** the rivals' consensus is the plain mean of the rivals' shares over the variable-level J, rebuilt on each
draw from that draw's shares. Its ranking uses C10's strict order (consensus share descending, then name).

**Why:** "RBO (p 0.9) of treeroute against the rivals' consensus (the mean of their shares, rebuilt per draw)".

**B1:** not used (section 10: B1 enters no consensus).
