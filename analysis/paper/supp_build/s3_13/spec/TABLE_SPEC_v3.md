# Table spec: Supplement S3.13 (Tables S3.18 to S3.30) and main-text Table 9

Written 2026-11-17 by the spec writer of the S3.13 tables workflow. Names: SHAP = `D:\treeroute\analysis\shap_v1`;
V = `SHAP\verify_v1`; ROOT = the research-paper folder (the parent of `engine\` and `paper\`); OUT =
`ROOT\paper\supp_build\s3_13`; `<X>` = a builder (A or B); `<p>` = a problem's data name (coral, fire, pm25, defo,
ndvi). Brief: `OUT\_brief\brief_tables.md`.

This spec is complete: a builder reads this file and the data files of section 1, and nothing else, and writes two
files, `OUT\<X>\tables.md` and `OUT\<X>\cells.json`, that are byte-identical to the other builder's. Every exact text
(captions, headers, labels, notes, constant cells) is given in a fenced block; copy it character for character and
replace only the `{placeholders}`. Where this spec says "stop", the builder stops with a message and writes neither
file (fail loud; never "fix" a value).

Contents: 0 Rules - 1 Sources - 2 Conventions (names, order, formats, layout) - 3 Checks before building - 4 The
tables - 5 cells.json - 6 Decisions - 7 Questions - 8 What the spec writer opened - 9 Version 2 (2026-11-17) - 10 Version 3 (2026-11-17).

---

## 0. Rules for the builders

- Python only as `py -3.9 -I -B <script>`, scripts in `OUT\<X>\scripts\`; no pip, no new packages (json, re,
  hashlib, numpy, pandas, pyarrow). Read-only on every existing file. Write only `OUT\<X>\tables.md`,
  `OUT\<X>\cells.json` and your own scripts.
- Open only the files of section 1. Never open `AW3_table.md`, `AW4_table.md`, `V\reconcile\report.md` (or its
  earlier versions), the other builder's folder, or `SHAP\smoke\bardl_fix\`. Never Grep or Glob over SHAP with a
  `*.md` pattern. Run no script of `SHAP\scripts`, `V` or `V\_lead\scripts`.
- Compute every printed number from a stored value with ONE formatting call (section 2.5). Never round a value and
  then format it, never format a formatted string again, never copy a number from a printout.
- Never write user names, e-mail addresses, user-folder names, host names, session ids or workflow ids into any file
  or output. Name files as in this spec (SHAP\..., V\..., OUT\..., D:/treeroute/...), never by ROOT's full path.
- Encoding of both outputs: UTF-8 without a byte-order mark, line feeds only (`\n`), no tab, no trailing space on any
  line, one final `\n` after the last line and no blank line at the end. Write each with
  `open(path, "w", encoding="utf-8", newline="\n")`. Under `-I` Python ignores `PYTHONIOENCODING`, so printing a
  non-ASCII character (−, ×, ᵃ, ...) to the console fails with the Windows code page; call
  `sys.stdout.reconfigure(encoding="utf-8")` first, or print ASCII only.

---

## 1. Sources (open these and only these)

Per problem `<p>`, folder `C = SHAP\out\<p>\lead_0\compare\`:

| File | Read | Keys or columns used |
|---|---|---|
| `C\per_lead.json` | `json.load` (it holds `NaN` tokens; Python's json accepts them) | `models`, `main_set`, `declined_by_guard`, `links`, `rows`, `regions`, `draws`, `draws_sha256`, `sample_sha256`, `families`, `nonzero_forecast_rows`, and per level `L` in (`variable`, `feature`): `players`, `active`, `structural_zero`, `nonzero_players`, `kendall_w_main_set`, `mean_pairwise_spearman_main_set`, `stability_under_region_resampling` |
| `C\AW4_main_row.json` | `json.load` (NaN tokens) | `models_in_main_set`, `reference_link`, `cross_link_models`, `declined_models`, `kendall_w`, `treeroute_vs_same_link_rivals_median_spearman_top20_union`, `["rbo_vs_consensus_p0.9"]`, `treeroute_top3`, `consensus_top3`, `own_history_share_treeroute`, `own_history_share_median_rival` (fire holds only the first four and `kendall_w`) |
| `C\pairs.parquet` | `pandas.read_parquet` | columns `level`, `model_a`, `model_b`, `pair_label`, `statistic`, `value`, `ci_low`, `ci_high`, `finite_replicates`, `signs_compared`; `model_a` < `model_b` in Python string order; statistics `spearman`, `spearman_top20_union`, `kendall_tau_b`, `jaccard_top5`, `jaccard_top10`, `jaccard_top20` (feature level, only where J has 200 or more players), `rbo_p0.9`, `rbo_p0.95`, `tvd`, `tvd_family` (variable level only), `sign_agreement_top10` |
| `C\importance.parquet` | `pandas.read_parquet` | `level`, `model`, `player`, `active`, `mean_abs`, `share` |
| `C\families.parquet` | `pandas.read_parquet` | `model`, `family`, `share` (variable level; families `own history`, `global indices`, `local drivers`, `context and calendar`, `seasonal normal`) |
| `C\bootstrap_draws.npy` | raw bytes only | SHA-256 of the whole file (check 3.1) |

Per problem and model `m` of `per_lead.json` `models`, folder `P = SHAP\out\<p>\lead_0\<m>\`:

| File | Keys used |
|---|---|
| `P\meta.json` | `rows`, `pass`, `checks_passed` (`S-ADD`, `S-EVAL`, `S-RESID`, `S-ZERO`), `link`, `guard.passed`, `max_abs_additivity_error`, `max_abs_additivity_error_variable`, `structural_zero_violations`, `sample_sha256`; treeroute also `pairs`, `arm` |
| `P\exactness.json` | every rival: `pass`, `rows`, `bit_equal_rows`, `max_abs_diff`, and `raw.bit_equal_rows` when the key `raw` exists (BARDL) |
| `P\ridge_shap_exactness.json` | `rival_ridge` of fire, pm25, defo and ndvi only: `pass`, `stage`, `rows`, `bit_equal_rows`, `max_abs_diff`, `raw.bit_equal_rows` |

treeroute's rebuild record `SHAP\rebuild\<p>\lead_0\gates.json`: `stopped_at`, `result` (`link`, `table_kind`,
`weighted`, `kind`) and `gates.<gate>.pass` and `.values` for the gates of Table S3.21.

The registered samples: `SHAP\SAMPLE_REGISTER.txt` (one line per problem; space-separated `key=value` fields after the
time stamp; fields `problem`, `n`, `sample`) and `SHAP\sample\<p>\sample_manifest.json` (`n`, `frame_rows`,
`regions_in_sample`, `units_in_sample`, `background_rows["0"]` with `min`, `median`, `max`, and
`sha256["sample.parquet"]`).

The B1 runs (fire, pm25, defo, ndvi): the log `SHAP\logs\tr_shap_<p>_lead0.log`; `SHAP\out\<p>\lead_0\treeroute_B1\meta.json`
(`pairs`, `tree_shap_seconds`) and `rows.parquet.done.json` (`seconds`), for checks only.

The independent re-computation: `V\A\results.json` (`json.load`; strict JSON). Used keys:

- `problems.<p>.levels.<L>.pairs["<a>|<b>"]` with `sign_agreement` (`value`, `ci_low`, `ci_high`, `n_finite`) and
  `sign_n_determined.value`; the pair key is the two data names in Python string order joined by `|`.
- `problems.fire.main_row.treeroute_top3` (list of `[name, share]`) and `problems.fire.main_row.own_history_share_treeroute`
  (`value`, `ci_low`, `ci_high`, `n_finite`).
- `b1.<p>.status.numbers`; for fire, pm25 and ndvi: `b1.<p>.run` (`pairs_log`, `total_seconds_log`,
  `tree_shap_seconds_log`), and per level `b1.<p>.<L>.pair_main_b1` (`n_J`, `spearman_J`, `spearman_top20_union`,
  `kendall_tau_b`, `jaccard_top5`, `jaccard_top10`, `jaccard_top20`, `rbo_p090`, `rbo_p095`, `tv_shares`,
  `tv_family_shares`, `sign_agreement`, `sign_n_determined`, `sign_n_agree`), `b1.<p>.<L>.importance.n_nonzero`,
  `b1.<p>.<L>.top10`, and at the variable level `b1.<p>.variable.families.<f>` (`own_history`, `global_indices`,
  `local_drivers`, `context_and_calendar`, `seasonal_normal`), `b1.<p>.variable.top3`,
  `b1.<p>.variable.own_history_share`; for defo `b1.defo.identity` (`max_abs_diff_phi`, `max_abs_diff_phiv`,
  `same_rows`, `same_players`, `same_variables`, `n_rows_main`, `n_rows_b1`, `n_players_main`, `n_players_b1`,
  `n_variables_main`, `n_variables_b1`, `as_expected`, `pairs_log`, `total_seconds_log`, `tree_shap_seconds_log`).
- An interval object is `{value, ci_low, ci_high, n_finite}`; `null` means undefined; a count's interval object is
  read for its `value` only.

The BARDL tie maxima: `V\_lead\outputs\bardl_maxima.txt`, its first block ("== BARDL pair-levels", lines 2-7). Each
line matches

```
^\s+(jaccard_top5|jaccard_top10|jaccard_top20|rho20|rbo090|rbo095)\s+spread ([0-9.]+) -> \S+ \(3 sig\. \S+\) at (\w+)/(\w+)/(\S+); values ([0-9.\-]+) / ([0-9.\-]+) / ([0-9.\-]+)$
```

with groups: statistic, spread, problem, level, pair key, and the values under the three collations (code-point
ascending, case-insensitive ascending, descending). Use only the first block (stop if any of the six statistics is
missing there or appears twice in it).

Text formats (version 2, G2): `SHAP\SAMPLE_REGISTER.txt` and the logs `SHAP\logs\tr_shap_<p>_lead0.log` have CRLF
line ends; `V\_lead\outputs\bardl_maxima.txt` has a UTF-8 byte-order mark and CRLF line ends. Read each of them as text
with universal newlines and encoding `utf-8-sig` (`open(path, encoding="utf-8-sig")`, whose default `newline=None`
turns every `\r\n` into `\n`), and split the text on `\n`. Line numbers (the selectors of section 5) count from 1 on
the lines so read; the register's fields, the maxima regex above and the two log regexes of section 4.10 (the "done
in" regex ends in `$`) are applied to a line without its line end.

Nothing else is opened: not `compare_shap.py`, not the rows files, not the printouts, not the protocol (its words that
the tables need are written into this spec), and not `C\bootstrap_stats.parquet` (the per-draw values of four pair
statistics, one row per level, pair and draw; the tables print the intervals already stored in pairs.parquet).

Which stored numbers carry an interval and a finite count:

- pairs.parquet: every statistic has `ci_low`, `ci_high` and `finite_replicates`, except that the sign agreement's are
  NaN, NaN and 0 although no draw was evaluated: those three are never printed (ruling BB1); the sign agreement's
  interval and finite count come from `V\A\results.json`, its value and `signs_compared` from pairs.parquet.
- per_lead.json: `kendall_w_main_set` and `mean_pairwise_spearman_main_set` have `value`, `ci` (two ends) and
  `finite_replicates`; the stability, the nonzero counts and the nonzero-forecast top 10 have none.
- AW4_main_row.json: each interval is `ci = [low, high, finite replicates]`; the median's `range` has no interval.
- importance.parquet and families.parquet: full-sample values only (no interval is printed for them, ruling BB5).
- `V\A\results.json`: interval objects `{value, ci_low, ci_high, n_finite}` for every statistic and share (B1's family
  shares and own-history share are printed with theirs); a count's interval is never printed.

---

## 2. Conventions

### 2.1 Problems

Order everywhere (the paper's order, Tables 1, 4a and 6): pm25, ndvi, fire, defo, coral.

| Data name | Display (start of a cell or a header) | Inline |
|---|---|---|
| pm25 | `PM2.5` | `PM2.5` |
| ndvi | `NDVI` | `NDVI` |
| fire | `Burned fraction` | `burned fraction` |
| defo | `Forest loss` | `forest loss` |
| coral | `Coral bleaching` | `coral bleaching` |

### 2.2 Models

Display order everywhere (Table 6's column order, then the published rival): treeroute, rival_ridge, rival_rf,
rival_lgbm, rival_lgbm_tweedie, rival_hgb_l1, rival_bardl_h1. A list of models is always printed in this order,
whatever the order of the source list.

| Data name | Inline (in cells, lists, pair names) | Header (column header) |
|---|---|---|
| treeroute | `treeroute v1` | `treeroute v1` |
| rival_ridge | `Ridge` | `Ridge` |
| rival_rf | `random forest` | `Random forest` |
| rival_lgbm | `LightGBM` | `LightGBM` |
| rival_lgbm_tweedie | `Tweedie booster` | `Tweedie booster` |
| rival_hgb_l1 | `absolute-error booster` | `Absolute-error booster` |
| rival_bardl_h1 | `BARDL` | `BARDL` |

A list of models in a cell: inline names joined by `, ` (comma, space); an empty list prints `none`.

A pair is printed `{first} vs {second}` with the two inline names, the earlier model in the display order first
(for example `treeroute v1 vs LightGBM`, `Ridge vs random forest`). Pairs that contain rival_bardl_h1 get `‡`
appended to this text in Table S3.24 (section 4.7).

### 2.3 Links

The link of a model is the part of its link string (per_lead.json `links`, AW4 `reference_link`) before the first
`|`; in gates.json `result.link`. Display:

| Link | Display |
|---|---|
| identity | `identity` |
| log_c | `log(y + c)` |
| log_mu | `log μ` |
| arcsine | `arcsine` |

Never print a raw link string (it holds `|`).

### 2.4 Players and variables

Variables and features (players) keep their data names, printed in backticks: `` `hist_last` ``, `` `x__hist_last_1` ``,
`` `c__ctx:sin1` ``, `` `normal` ``. A list of names ("name list"): backticked names joined by ", ", in the order of
the source list (rank order for a top-k list; the stored order for the structural zeros); never re-sorted. Model data
names, where a table shows them (Table S3.18), are backticked too.

### 2.5 Number formats (one call per printed number)

The characters used below: `−` U+2212 MINUS SIGN; `–` U+2013 EN DASH; `×` U+00D7; `μ` U+03BC; superscripts `⁰`
U+2070, `¹` U+00B9, `²` U+00B2, `³` U+00B3, `⁴` U+2074, `⁵` U+2075, `⁶` U+2076, `⁷` U+2077, `⁸` U+2078, `⁹` U+2079,
`⁻` U+207B; marks `†` U+2020, `‡` U+2021, `§` U+00A7, `ᵃ` U+1D43, `ᵇ` U+1D47, `ᶜ` U+1D9C, `ᵈ` U+1D48. Apostrophes
are ASCII `'`.

Python's `format(x, '.2f')` rounds the exact binary value of the double correctly, with ties to even (an exactly
representable 0.625 prints `0.62`; the data hold such ties). Use exactly the calls below; never `round()`, numpy
rounding or `decimal` with another rounding mode. Every value is a Python float, int or bool before it is formatted
or stored (numpy scalars from parquet are converted with `.item()`).

```
NUM2(x):  statistic with two decimals
    stop if x is None or not finite (undefined values are handled before NUM2 is called)
    if x == 0.0: return "0.00"                     (also for -0.0)
    s = format(x, ".2f")
    if s[0] == "-": s = "−" + s[1:]                (a negative value that rounds to zero prints "−0.00")
    return s

PCT1(x):  share in percent with one decimal
    stop if x is None, not finite, or x < 0
    if x == 0.0: return "0.0%"
    y = 100.0 * x
    if y < 0.05: return "<0.1%"                     (a positive share is never shown as the exact zero)
    return format(y, ".1f") + "%"

COUNT(n): integer count with thousands separators
    stop unless n is an int, or a float with n.is_integer()
    return format(int(n), ",")                      (91440 -> "91,440"; 254 -> "254")

SCI2(x):  check magnitude, two significant digits
    if x == 0.0: return "0"
    m, e = format(abs(x), ".1e").split("e")         (2.1316282072803006e-14 -> "2.1", "-14")
    sup = int(e) written with the superscript digits and ⁻
    return ("−" if x < 0 else "") + m + " × 10" + sup        ("2.1 × 10⁻¹⁴")

SECS(x):  seconds from a log line
    return format(x, ",.1f")                        (17890.4 -> "17,890.4")

MED(x):   a median of row counts: COUNT(x) if float(x).is_integer() else format(x, ".1f")
```

Self-test vectors for the format functions (synthetic values, not data): NUM2(0.625) = `0.62`; NUM2(0.875) = `0.88`;
NUM2(-0.004) = `−0.00`; NUM2(-0.0) = `0.00`; NUM2(-0.1214) = `−0.12`; PCT1(0.0625) = `6.2%`; PCT1(0.0002) = `<0.1%`;
PCT1(0.0) = `0.0%`; PCT1(0.14169933950641164) = `14.2%`; COUNT(1140) = `1,140`; COUNT(10.0) = `10`;
SCI2(9.237055564881302e-14) = `9.2 × 10⁻¹⁴`; SCI2(2.220446049250313e-16) = `2.2 × 10⁻¹⁶`; SECS(2636.6) = `2,636.6`.

### 2.6 Composite cells

Let `D` = per_lead.json `draws` (2000 on every problem, check 3.1).

```
CI2(v, lo, hi, nf):   a statistic with its interval
    head = NUM2(v) if v is finite else "undefined"
    if nf is None or nf == 0: return head if v is finite else "undefined"     (no interval to print)
    s = head + " [" + NUM2(lo) + ", " + NUM2(hi) + "]"
    if nf < D: s += " (" + COUNT(nf) + " finite draws)"
    return s

CIP(v, lo, hi, nf):   a share with its interval: as CI2 with PCT1 in place of NUM2

SIGN(v, k, lo, hi, nf):   sign agreement (v and k from the comparison, lo, hi, nf from the re-computation)
    head = NUM2(v) if v is finite else "undefined"
    if nf > 0: head += " [" + NUM2(lo) + ", " + NUM2(hi) + "]"
    extras = [COUNT(k) + (" sign" if k == 1 else " signs")]
    if 0 < nf < D: extras.append(COUNT(nf) + " finite draws")
    return head + " (" + "; ".join(extras) + ")"

TOP(name, share):  "`" + name + "` " + PCT1(share)
```

Examples of the shapes (synthetic): `0.71 [0.65, 0.80]`; `undefined`; `0.42 [0.30, 0.55] (812 finite draws)`;
`0.88 [0.78, 0.92] (8 signs)`; `1.00 [0.00, 1.00] (1 sign; 1,140 finite draws)`; `undefined [0.00, 1.00] (0 signs;
64 finite draws)`; `undefined (0 signs)`; `13.6% [10.8%, 16.5%]`; `` `spei` 3.3% ``.

### 2.7 Undefined, empty and labelled cells

- `undefined`: a statistic the data define but that has no finite value on the full sample (a NaN in the comparison
  files, a `null` value in `V\A\results.json`): Kendall's W of a one-model main set, a sign agreement with no
  qualifying player. It gets a cells.json entry (section 5) with `stored` `[null]`.
- `–` (U+2013): a cell that does not apply: fire's main-row cells that need a rival (the comparison writes no key for
  them and the re-computation leaves them undefined by design), a top-20 Jaccard whose pair J has fewer than 200
  players, a clipped column the check did not read. No cells.json entry.
- A family with no variable in a problem (per_lead.json `families` maps no variable to it) keeps its defined 0 with
  a label appended after one space (ruling BB4):

| Family | Label |
|---|---|
| own history | `(no own-history input)` |
| global indices | `(no global-index input)` |
| local drivers | `(no local-driver input)` |
| context and calendar | `(no context or calendar input)` |
| seasonal normal | `(no seasonal-normal input)` |

  In these data only coral's own history and defo's context and calendar have no variable (check 3.6).

### 2.8 Marks and notes

| Mark | Meaning | Ruling |
|---|---|---|
| `†` | a number from the independent re-computation (`V\A\results.json`, A = B) that the comparison files do not hold | BB1 |
| `‡` | BARDL's ranking beyond its three variables (nine columns) is filled by name order, and so are its top-k sets where they reach that far (footnote with the spreads over the three collations) | BB3 |
| `§` | the feature-level family-share distance is the variable-level value repeated | BB2 |
| `ᵃ ᵇ ᶜ ᵈ` | ordinary notes, lettered per table | |

A mark is appended to a cell or header text with no space before it (`0.37 [0.36, 0.57]ᵇ`, `Coral bleachingᵈ`). Note
lines follow the table, each note one line, in the order this spec gives.

### 2.9 Markdown layout

- A table: a header line, a separator line and one line per row, with no blank line between them.
  - A row line is `"| " + " | ".join(cells) + " |"`.
  - The separator is `"|" + "---|" * ncols`.
  - No padding: each cell is its text with no leading or trailing space.
  - No cell or header contains `|` or a line break (stop if one would).
- Blocks are separated by exactly one blank line. A block is one of: a heading line; a caption line; a panel label
  line; a table; a group of note lines (consecutive lines, no blank line between notes).
- The order within a table: caption line, then for each panel its label line and its table (a table without panels
  has neither label), then the table's note group (if it has notes), all separated by single blank lines.
- tables.md is, in this order: the header comment line; heading 1; Table 9; heading 2; Tables S3.18 to S3.27; heading
  3; Tables S3.28 to S3.30. Blocks separated by single blank lines; the file ends with the last note line of Table
  S3.30 followed by one `\n`.

Header comment (line 1):

```
<!-- Draft tables of Supplement S3.13 (Tables S3.18 to S3.30) and of the main-text Table 9: the post hoc SHAP comparison of scope (i), the nowcast of each problem. Version 2 (2026-11-17, after the first check): ten captions and notes and three table cells reworded, one row of Table S3.18 b dropped and one note line added; no number changed. Version 3 (2026-11-17, after the second check): captions, notes, labels, cells and source comments reworded, as paper/supp_build/s3_13/spec/CHANGES_v3.md lists; no number changed. Built from the stored values with one rounding step per printed number, by the rules of paper/supp_build/s3_13/spec/TABLE_SPEC.md; every printed data number is listed in cells.json beside this file (the constants of the fixed texts, such as 1,000 and 2,000, are not). Captions and notes are drafts: the text writers may polish the wording, never the numbers. Rulings AK (post hoc), BA1-BA3 and BB1-BB6 (engine/OWNER_RULINGS_2026-10-06.md). -->
```

Heading 1, heading 2 and heading 3:

```
## Main text: Table 9 (Section 5.4, Post hoc analyses)
```

```
## Supplement S3.13: SHAP comparison of the main runs
```

```
## Supplement S3.13: treeroute v1's B1 sensitivity (kept apart from the main set)
```

---

## 3. Checks before building (stop on any failure)

1. Per problem: per_lead.json `rows` == 1000 == SAMPLE_REGISTER `n` == manifest `n`; `draws` == 2000; the register's
   `sample` == manifest `sha256["sample.parquet"]` == per_lead.json `sample_sha256` == every piece's
   `meta.json` `sample_sha256`; SHA-256 of the bytes of `bootstrap_draws.npy` == `draws_sha256`; per_lead.json
   `regions` == manifest `regions_in_sample`.
2. Per problem: every model of per_lead.json `models` is in the table of 2.2 and has its folder; `treeroute_B1` is
   not in `models`; every model's `meta.json` has `rows` 1000, `pass` true, all four `checks_passed` true and
   `structural_zero_violations` 0; every rival's S-EXACT record (the table "The S-EXACT record of a model" in
   section 4.4) has `pass` true, and for rival_ridge of fire, pm25, defo and ndvi its `exactness.json` (the rivals' SHAP
   script's own row-by-row check, kept as a record) has `pass` false and its `ridge_shap_exactness.json` has `stage`
   `bits` and `pass` true; gates.json `stopped_at` is null.
3. Per problem and level: `pairs.parquet` holds every unordered pair of `models` once per statistic of that level;
   `jaccard_top20` exists at a level exactly when that level's `active` >= 200; `tvd_family` exists at the variable
   level only. Within each problem every link string has the same `c=` and `ub=` fields. A pair's `pair_label`
   starts with `same-link` exactly when its two link strings are equal, else with `cross-link (not comparable in
   scale or rank)`; it carries `; raw model, declined by its guard: <names>` exactly when one of the two models is in
   `declined_by_guard`, `<names>` being those models' data names joined by `, ` (the source label's own words; the
   Link cell of 4.7 prints "declined by its skill guard" in their place, version 3, V3-6).
4. Per pair and level, sign agreement: A's `sign_agreement.value` equals the comparison's `value` within 1e-12, or
   both are undefined (null, NaN); A's `sign_n_determined.value` equals `signs_compared`; if A's `n_finite` > 0 then
   `ci_low` and `ci_high` are numbers, if 0 then both are null.
5. Per problem and level and model: sorting the model's rows of `importance.parquet` with `active` true by
   (`-mean_abs`, `player`), the player names ascending in Python string order, gives the ranking; at the variable
   level treeroute's first three names equal AW4 `treeroute_top3` (fire: A's `problems.fire.main_row.treeroute_top3`
   names); fire's A own-history value equals families.parquet treeroute `own history` share within 1e-12.
6. Families with no variable (2.7) are exactly coral `own history` and defo `context and calendar`; families.parquet
   gives them share 0.0 for every model.
7. Main row (problems other than fire): AW4 `kendall_w.value` equals per_lead.json `variable.kendall_w_main_set.value`,
   AW4 `kendall_w.ci[0:2]` its `ci` and AW4 `kendall_w.ci[2]` its `finite_replicates`;
   AW4 `models_in_main_set` equals per_lead.json `main_set` as sets; the median's `range` equals the lowest and highest
   of `pairs.parquet` `spearman_top20_union` (variable level) of treeroute with each main-set rival, and the median of
   those values (numpy median) equals AW4's value, within 1e-12; AW4 `own_history_share_median_rival.value` equals the
   numpy median of the main-set rivals' families.parquet `own history` shares within 1e-12, and on pm25 and defo it
   equals rival_lgbm's share, on ndvi (four rivals) the mean of the two middle shares. Fire: `models_in_main_set` is
   `["treeroute"]`, `cross_link_models` is `["rival_lgbm", "rival_lgbm_tweedie", "rival_rf"]`, `declined_models` is
   `["rival_ridge"]`, AW4 `kendall_w` value is NaN with `ci` `[NaN, NaN, 0]`.
8. B1: A's `b1.<p>.status.numbers` is `none` for coral, `identity` for defo, `full` for fire, pm25 and ndvi;
   `b1.defo.identity.as_expected` is true. For defo, fire, pm25 and ndvi the log's B1 block (Table S3.30) has a
   set-up time at or after `2026-11-15 23:06:00`, its pairs equal A's `pairs_log` and treeroute_B1 `meta.json`
   `pairs`, its total seconds equal A's `total_seconds_log` and `rows.parquet.done.json` `seconds`, its tree-SHAP
   seconds equal A's `tree_shap_seconds_log` and `meta.json` `tree_shap_seconds` (floats compared exactly after
   parsing the log text).
9. BARDL (ndvi): per_lead.json `variable.nonzero_players.rival_bardl_h1` == 3 and
   `feature.nonzero_players.rival_bardl_h1` == 9; `aet_total_mm` is in BARDL's variable-level top 5 (check 5's order)
   with share 0.0; the six maxima lines exist (section 1); the first value on the jaccard_top5 line equals
   `pairs.parquet` `jaccard_top5` of that pair and level within 1e-9.
10. Gates (Table S3.21): every gate of that table that exists has `pass` true except `E5_bank_fingerprint`, which has
    `pass` false on all five problems; `E3m_recorded_path_map` exists exactly when `E3a_inputs_before_read.values.path_map`
    is true, and then every `values.files[i].equal` is true; `E5a_identity_twin` and `E7_gls_weight_model` exist exactly
    when `result.link` is arcsine and `result.weighted` is true respectively; `E4_donor_rows.values.rows[0] == rows[1]`
    and `row_key_hash[0] == row_key_hash[1]`; `E9...values.fits_whose_X_b_differs_from_the_kernel` == 0; treeroute's
    `meta.json` `arm` equals `{link}_{table_kind}_{gls if weighted else unweighted}` from `result`.

---

## 4. The tables

Order of appearance (the numbering continues Supplement S3 at Table S3.18):

| Id | Short caption title | Brief item |
|---|---|---|
| 9 | SHAP agreement between treeroute v1 and its rivals (main text) | 1 |
| S3.18 | The models explained, and the rivals left out | 8 |
| S3.19 | The registered samples, backgrounds and active sets | 10 |
| S3.20 | Checks of every explained model | 7 |
| S3.21 | treeroute v1's rebuild gates | 7 |
| S3.22 | The main-text row with its components | 6 |
| S3.23 | PM2.5: SHAP agreement of the models | 2, 3, 4 |
| S3.24 | NDVI: SHAP agreement of the models | 2, 3, 4 |
| S3.25 | Burned fraction: SHAP agreement of the models | 2, 3, 4, 5 |
| S3.26 | Forest loss: SHAP agreement of the models | 2, 3, 4 |
| S3.27 | Coral bleaching: SHAP agreement of the models | 2, 3, 4, 5 |
| S3.28 | B1 sensitivity: the pair (main run, B1 run) | 9 |
| S3.29 | B1 sensitivity: the B1 run's family shares, top 3 and top 10 | 9 |
| S3.30 | B1 sensitivity: run facts and forest loss's identity check | 9 |

For each table below: the caption line (exact, one line, ending with its source comment), the panels with their
label lines and header lines (exact), the row rule, the cell rules and the notes (exact). In the cell rules,
"pairs(p, L, a, b, s)" is the row of `pairs.parquet` with `level == L`, statistic `s` and the unordered pair {a, b};
"A" is `V\A\results.json`; "AW4" is `AW4_main_row.json`; "PL" is `per_lead.json`. A literal text inside a cell rule
is written in double quotes, exactly as printed, spaces included ("no: " is n, o, colon, space); `+` joins texts; a
text in backticks without quotes is printed as it stands.

### 4.1 Table 9 (main text)

Caption line:

```
**Table 9.** SHAP agreement between treeroute v1 and its rivals at the nowcast, variable level (post hoc). Computed after the test labels were opened, on a fixed sample of 1,000 test rows per problem; report-only, never deciding, and not headline results. Each model is explained in its own link space against a background of the same location's router fit rows of the same calendar month (forest loss, annual: all of them; coral bleaching: other sites' survey visits). A variable's importance to a model is its mean absolute SHAP value over the sample, with each region weighted equally; rankings order the variables by importance. Main set: treeroute v1 and its rivals that explain in its link and passed their skill guard. W: Kendall's W of the main set's rankings. Spearman: rank correlation over the union of two models' top-20 variables, here of treeroute v1 with each same-link rival. RBO: rank-biased overlap of treeroute v1's full ranking with the rivals' consensus (the mean of their importance shares). Own-history share: the share of the own-history family in the sum of the mean absolute attributions of the model's five families (with each region weighted equally), a family's attribution on a row being the sum of its variables' SHAP values; it is not the sum of the own-history variables' shares. The five families are own history (the lags and trailing means of the location's own labels), global indices, local drivers, context and calendar, and the seasonal normal. Percentile 95% intervals over 2,000 paired bootstrap draws of regions. Every pair, at both levels: Supplement S3.13. <!-- src: D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/compare/AW4_main_row.json (every number but the two cells marked with a dagger); D:/treeroute/analysis/shap_v1/verify_v1/A/results.json problems.fire.main_row (the cells marked with a dagger, ruling BB1); pairs.parquet, importance.parquet and families.parquet for checks only; rulings AK, BA1, BB1, BB4 -->
```

Header and separator (9 columns):

```
| Problem | Main set | W [95% CI] | Spearman of treeroute v1 with its same-link rivals: median [95% CI] (range) | RBO with the rivals' consensus, p = 0.9 [95% CI] | treeroute v1's top 3 | Consensus top 3 | Own-history share, treeroute v1 [95% CI] | Own-history share, median of the rivalsᶜ [95% CI] |
|---|---|---|---|---|---|---|---|---|
```

Rows: one per problem in the order of 2.1.

Cells (problems other than fire; AW4 intervals are `ci = [low, high, finite]`):

| Column | Cell |
|---|---|
| Problem | display name (2.1) |
| Main set | AW4 `models_in_main_set` as a model list (2.2) |
| W | CI2(AW4 `kendall_w.value`, `ci[0]`, `ci[1]`, `ci[2]`) |
| Spearman | CI2 of AW4 `treeroute_vs_same_link_rivals_median_spearman_top20_union` (`value`, `ci[0]`, `ci[1]`, `ci[2]`) + " (" + NUM2(`range[0]`) + " to " + NUM2(`range[1]`) + ")" |
| RBO | CI2 of AW4 `["rbo_vs_consensus_p0.9"]` (`value`, `ci[0]`, `ci[1]`, `ci[2]`); on pm25 append `ᵇ` |
| treeroute v1's top 3 | AW4 `treeroute_top3` as a name list (2.4) |
| Consensus top 3 | AW4 `consensus_top3` as a name list |
| Own-history share, treeroute v1 | CI2 of AW4 `own_history_share_treeroute`; on coral append " (no own-history input)" |
| Own-history share, median of the rivals | CI2 of AW4 `own_history_share_median_rival`; on coral append " (no own-history input)" |

Fire's row, exactly these cells: `Burned fraction`; `treeroute v1 onlyᵃ`; `undefined` (from AW4 `kendall_w.value`, NaN);
`–`; `–`; A's `problems.fire.main_row.treeroute_top3` names as a name list + `†`; `–`; CI2 of A's
`problems.fire.main_row.own_history_share_treeroute` (`value`, `ci_low`, `ci_high`, `n_finite`) + `†`; `–`.

The two share bases (PROTOCOL section 8; version 2, C1). A player's share (importance.parquet `share`, the top-k
shares) is its mean absolute SHAP value divided by the model's total mean absolute SHAP value over J. A family share
(families.parquet `share`) is the family's mean absolute attribution divided by the sum of the model's five families'
mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values on that row.
The own-history shares of Table 9 (AW4 `own_history_share_treeroute` and `own_history_share_median_rival`; A's
`problems.fire.main_row.own_history_share_treeroute`) are family shares, not the sum of the own-history variables'
shares, as the caption says. The region weighting (version 3, V3-1): every mean absolute value in the two bases
weights each region equally. A player's importance (importance.parquet `mean_abs`, by which check 3.5 ranks the
players) is the region-weighted mean of its absolute SHAP values over the sample rows, as PROTOCOL section 8 defines
it ("I_m(j): the region-weighted mean |phi_ij| (each region weighs 1)"), and the model's total is the sum of these
over J; a family's mean absolute attribution is weighted the same way (the second check,
`OUT\skeptic\k08_share_bases.py`, found this for families.parquet, panel g and A's B1 values). The captions of
Table 9 and of Tables S3.19, S3.23 to S3.27 and S3.29 state it.

Notes (exact, in this order):

```
ᵃ Burned fraction: every rival explains in another link (LightGBM, the random forest and Ridge in log(y + c), the Tweedie booster in log μ), and Ridge also failed its skill guard, so the main set is treeroute v1 alone. W needs two models and is undefined, and the cells that need a rival are empty (–): agreement between treeroute v1 and a rival cannot separate the link from the model there. The cross-link pairs are in Table S3.25.
ᵇ PM2.5: the interval of the RBO with the consensus is asymmetric because the consensus's top variable changes across the region draws.
ᶜ The median of the main-set rivals' own-history shares: on PM2.5 and forest loss LightGBM's share; on NDVI, with four rivals, the mean of the two middle shares.
† From the independent re-computation of the comparison (two implementations that agree): the comparison's output files leave these two cells empty, because they are written only when treeroute v1 has a same-link rival.
```

cells.json keys: row = problem data name; columns `kendall_w` (parts `value`, `ci_low`, `ci_high`, and `n_finite`
only when printed), `spearman_top20_union_median` (`value`, `ci_low`, `ci_high`, `range_min`, `range_max`),
`rbo_vs_consensus` (`value`, `ci_low`, `ci_high`), `own_history_treeroute` and `own_history_median_rivals` (`value`,
`ci_low`, `ci_high`). Fire's `undefined` W is an entry (part `value`, stored `[null]`).

### 4.2 Table S3.18: the models explained, and the rivals left out

Caption line:

```
**Table S3.18 (post hoc).** The models explained at the nowcast (a), and the rivals and naive baselines left out, with the reason (b). <!-- src: D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/compare/per_lead.json (models, links, main_set, declined_by_guard); D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/<model>/meta.json (guard.passed); D:/treeroute/analysis/shap_v1/PROTOCOL.md sections 5 and 7 and engine/PENDING_PARTS.md Part 628 (methods; rivals left out and why); paper/draft/03_protocol.md Section 3.3, paper/draft/tables/table_3.md note d and paper/draft/GLOSSARY.md (naive baseline, trees-off fit, reference) for the naive baselines; paper/draft/tables/table_6.md (Table 7) for the rivals at forecast leads only; rulings AW2, AY1, BA1 -->
```

Panel a label, header:

```
**a. Explained models.**
```

```
| Problem | Model (data name) | Model and SHAP method | Link | Skill guard at the nowcast | In the main set |
|---|---|---|---|---|---|
```

Rows: problems in the order of 2.1; within a problem, per_lead.json `models` in the display order of 2.2.

| Column | Cell |
|---|---|
| Problem | display name |
| Model (data name) | inline name + " (" + a backtick + data name + a backtick + ")" (for example ``Ridge (`rival_ridge`)``) |
| Model and SHAP method | the constant below for the model |
| Link | display (2.3) of the model's link in PL `links` |
| Skill guard at the nowcast | treeroute: `passed (the adopted arm)`; a rival: `passed` if `meta.json` `guard.passed` is true, else `failedᵃ` |
| In the main set | `yes` if the model is in PL `main_set`; else "no: " + the reasons joined by "; " among `another link` (its link string differs from treeroute's) and `skill guard failed` (it is in `declined_by_guard`), in that order |

Constants for "Model and SHAP method":

| Model | Text |
|---|---|
| treeroute | `the adopted arm: tree bank and router; exact interventional TreeSHAP of the trees, router terms exactly linear` |
| rival_ridge | `ridge regression; exact linear SHAP` |
| rival_rf | `random forest, rebuilt from the rival board's records; exact interventional TreeSHAP` |
| rival_lgbm | `LightGBM; exact interventional TreeSHAP` |
| rival_lgbm_tweedie | `LightGBM with a Tweedie loss; exact interventional TreeSHAP` |
| rival_hgb_l1 | `gradient booster on absolute error; exact interventional TreeSHAP` |
| rival_bardl_h1 | `published rain-lag Bayesian distributed-lag model, per location; exact linear SHAP over its nine input columns` |

Panel b label, header, rows (all constant, exactly):

```
**b. Rivals and naive baselines left out.**
```

```
| Problem | Rival | Why it has no SHAP value |
|---|---|---|
| PM2.5 | MERRA-2 PM2.5: lagged one month, same month, and the placebo entry | One-input calibration maps of the product, fitted per location: the attribution would be 100% on that one input. |
| PM2.5 | CAMS EAC4 | Never run: not obtained (ruling AG1). |
| NDVI | LSTM of Kraft et al. (2019) | Not bit-reproducible without its original deep-learning library, so left out until the owner rules (decision D7); its skill guard failed at the nowcast. |
| Burned fraction | The published rivals, among them the CEMS seasonal fire weather index forecast (SEAS5) | Never run (ruling AS). |
| Forest loss | VT0007, calibrated | One-input map (isotonic on anomalies): the attribution would be 100% on that one input. |
| Forest loss | VT0007, as shipped; VT0007, frozen at 2019 | Not a function of the rows' input columns: the index value as the product gives it. |
| Coral bleaching | NOAA Coral Reef Watch degree heating weeks (nowcast rule) | One-input map (isotonic on degree heating weeks): the attribution would be 100% on that one input. |
| All five | The naive baselines at the nowcast: the arithmetic and last-5-years normals, predict-zero and each link's trees-off fit, which equals that link's normal exactly and is the reference of the arms in that link; on coral bleaching, which has no per-location normal, the training median (its reference) and predict-zero | No input feature: there is no SHAP value to compute. |
```

Notes (exact):

```
Panel b lists the nowcast's rivals and naive baselines that have no SHAP value; rivals that run only at forecast leads (Table 7), among them the CRW Outlook, are outside this comparison, which explains the nowcast only.
ᵃ Failed: the raw model is explained, labelled, and kept out of Kendall's W, the consensus and the main-text row (decision D6).
Links: identity; log(y + c), with c the problem's constant; log μ, the log of the Tweedie booster's mean; arcsine, the arcsine square root. Within each problem every model has the same c and upper bound, so two models are same-link exactly when their links are the same. The main set is treeroute v1 with its same-link rivals that passed their skill guard.
```

cells.json: Table S3.18 prints no data number (no entries).

### 4.3 Table S3.19: the registered samples, backgrounds and active sets

Caption line:

```
**Table S3.19 (post hoc).** The registered samples, their backgrounds and the active sets, nowcast. J: the players to which some model gives more than 10⁻¹² of its total mean absolute SHAP value (with each region weighted equally); the others are structural zeros. <!-- src: D:/treeroute/analysis/shap_v1/SAMPLE_REGISTER.txt (n, sample); D:/treeroute/analysis/shap_v1/sample/<problem>/sample_manifest.json (frame_rows, regions_in_sample, units_in_sample, background_rows); D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/treeroute/meta.json (pairs); D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/compare/per_lead.json (players, active, structural_zero) -->
```

Header:

```
| Problem | Frame rowsᵃ | Sample rows | Regions | Locationsᵇ | Background rows per sample rowᶜ | Background pairs | Feature level: players / J / structural zeros | Variable level: players / J / structural zeros |
|---|---|---|---|---|---|---|---|---|
```

Rows: problems in the order of 2.1. Cells:

| Column | Cell |
|---|---|
| Problem | display name |
| Frame rows | COUNT(manifest `frame_rows`) |
| Sample rows | COUNT(register `n`, parsed as int) |
| Regions | COUNT(manifest `regions_in_sample`) |
| Locations | COUNT(manifest `units_in_sample`) |
| Background rows | with b = manifest `background_rows["0"]`: COUNT(b.min) if b.min == b.max, else COUNT(b.min) + "–" + COUNT(b.max) + " (median " + MED(b.median) + ")" (U+2013 between the two counts, no spaces) |
| Background pairs | COUNT(treeroute `meta.json` `pairs`) |
| Feature level | COUNT(PL `feature.players`) + " / " + COUNT(PL `feature.active`) + " / " + COUNT(len(PL `feature.structural_zero`)) |
| Variable level | the same with `variable` |

Notes (exact first four lines; then one line per problem):

```
ᵃ Frame: the labelled test rows that every compared model covers; the sample is drawn from it, stratified by region and test year.
ᵇ Coral bleaching: a location is a survey visit.
ᶜ Background (B2): the same location's router fit rows of the sample row's calendar month at or before the cut (forest loss, annual: all of them); coral bleaching: the survey visit's saved router fit rows, a pool of other sites' survey visits. Shown as the lowest to highest number per sample row, with the median.
Structural zeros (exactly 0 in every model at that level, so outside J):
```

then, for each problem in the order of 2.1, one line:

```
{Problem}: variable level ({nv}) {names_v}; feature level ({nf}) {names_f}.
```

with `{Problem}` the display name, `{nv}` = COUNT(len(PL `variable.structural_zero`)), `{names_v}` the list
PL `variable.structural_zero` in its stored order as a name list (2.4), and the same for the feature level.

cells.json keys: row = problem; columns `frame_rows`, `sample_rows`, `regions`, `locations`, `background_rows`
(parts `min`, `max`, `median`; when min == max only `min`), `background_pairs`, `feature` and `variable` (parts
`players`, `J`, `structural_zeros`; the structural-zero count's stored value is the list's length, its selector
`len(feature.structural_zero)`). Note numbers: row `note`, column `structural_zeros:{p}:{level}`, part `count`.

### 4.4 Table S3.20: checks of every explained model

Caption line:

```
**Table S3.20 (post hoc).** Checks of every explained model, nowcast: the rebuild or reload reproduces the saved predictions (S-EXACT), the attributions add up to the model's output (S-ADD), its evaluator equals the model (S-EVAL), the unattributed part stays small (S-RESID), and a player that equals the explained row on every background row gets exactly 0 (S-ZERO). <!-- src: D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/<model>/exactness.json, ridge_shap_exactness.json (Ridge outside coral bleaching) and meta.json; D:/treeroute/analysis/shap_v1/rebuild/<problem>/lead_0/gates.json (treeroute v1, gate E8); D:/treeroute/analysis/shap_v1/PROTOCOL.md sections 4 and 11 -->
```

Header:

```
| Problem | Model | Rows checkedᵃ | Bit-identical rows, pre-clip / clippedᵃ | Largest absolute difference, rebuilt − saved (pre-clip, y units) | S-EXACT | Largest additivity error, feature / variable level | S-ZERO violations | S-ADD, S-EVAL, S-RESID, S-ZERO | Skill guard |
|---|---|---|---|---|---|---|---|---|---|
```

Rows: as Table S3.18 panel a (problems in order, models in display order).

The S-EXACT record of a model (also used by check 3.2):

| Model | Record | rows | pre | clipped | max |
|---|---|---|---|---|---|
| treeroute | gates.json `gates.E8_predictions.values` | `rows_checked` | `pre_bit_equal` | `arm_bit_equal` | `max_abs_pre` |
| rival_ridge of fire, pm25, defo, ndvi | `ridge_shap_exactness.json` | `rows` | `bit_equal_rows` | `raw.bit_equal_rows` | `max_abs_diff` |
| a rival whose `exactness.json` has the key `raw` (BARDL) | `exactness.json` | `rows` | `bit_equal_rows` | `raw.bit_equal_rows` | `max_abs_diff` |
| every other rival | `exactness.json` | `rows` | `bit_equal_rows` | not read | `max_abs_diff` |

Cells:

| Column | Cell |
|---|---|
| Problem | display name |
| Model | inline name; for rival_ridge of fire, pm25, defo and ndvi append `ᵇ` |
| Rows checked | COUNT(rows) |
| Bit-identical rows | COUNT(pre) + " / " + (COUNT(clipped) if read, else "–") |
| Largest absolute difference | SCI2(max) |
| S-EXACT | rivals: `bit-identical` (stop unless pre == rows and, if read, clipped == rows). treeroute: `bit-identical` if E8 `bit_identical` is true; else (stop unless `within_relative_tolerance` is true and `rows_outside_tolerance` == 0) "within the D8 toleranceᶜ (largest relative difference " + SCI2(E8 `max_rel_pre`) + ")" |
| Largest additivity error | SCI2(`meta.json` `max_abs_additivity_error`) + " / " + SCI2(`max_abs_additivity_error_variable`) |
| S-ZERO violations | COUNT(`meta.json` `structural_zero_violations`) |
| S-ADD, S-EVAL, S-RESID, S-ZERO | `all passed` (check 3.2) |
| Skill guard | treeroute: `passed (the adopted arm)`; a rival: `passed` if `meta.json` `guard.passed` is true, else `failedᵈ` |

Notes (exact; the placeholders of note ᵇ come from `SHAP\out\<p>\lead_0\rival_ridge\exactness.json`, rival_shap.py's
own failed check, for p in pm25, ndvi, fire, defo: `{bit_<p>}` = COUNT(`bit_equal_rows`), `{rows_<p>}` =
COUNT(`rows`)):

```
ᵃ Rows checked: every test row of the rival's saved predictions; for treeroute v1, every test row of every sampled location (coral bleaching: every test survey visit). Pre-clip: the prediction before the declared bounds are applied; clipped: after. The rivals' SHAP script (rival_shap.py) checks a rival's pre-clip column only (–: not read).
ᵇ Ridge outside coral bleaching is explained by a loader that repeats the rival board's own block-wise scoring, which reproduces every saved prediction. The rivals' SHAP script's own check of its row-by-row copy of the design, kept as a record, matched {bit_pm25} of {rows_pm25} rows on PM2.5, {bit_ndvi} of {rows_ndvi} on NDVI, {bit_fire} of {rows_fire} on burned fraction and {bit_defo} of {rows_defo} on forest loss, because that copy adds the same terms in another order.
ᶜ D8: on the arcsine arms of burned fraction and coral bleaching the owner allowed a relative difference of at most 10⁻¹² (ruling AY3), licensed by the bit-identical identity-link twin (gate E5a, Table S3.21).
ᵈ Failed: the raw model is explained, labelled, and kept out of Kendall's W, the consensus and the main-text row (decision D6).
```

cells.json keys: row = `{p}:{model}`; columns `rows_checked`, `bit_identical` (parts `pre`, `clipped`), `max_abs_diff`,
`s_exact` (part `max_rel` on the D8 rows only), `additivity` (parts `feature`, `variable`), `s_zero_violations`.
Note numbers: row `note`, columns `ridge_copy:{p}` with parts `bit_equal_rows`, `rows`.

### 4.5 Table S3.21: treeroute v1's rebuild gates

Caption line:

```
**Table S3.21 (post hoc).** treeroute v1's rebuild gates, nowcast, in the order they run. The fitted trees were not kept, so each problem's tree bank and the sampled locations' routers were rebuilt with the run's own engine code; a failed gate stops the problem, except E5, which is informational. <!-- src: D:/treeroute/analysis/shap_v1/rebuild/<problem>/lead_0/gates.json (result; gates.<gate>.pass and .values); D:/treeroute/analysis/shap_v1/PROTOCOL.md sections 4.1 and 11; rulings AY2 (path map, gate E3m) and AY3 (D8) -->
```

Header:

```
| Gate | What it checks | PM2.5 | NDVI | Burned fraction | Forest loss | Coral bleaching |
|---|---|---|---|---|---|---|
```

Rows, in this order; "Gate" and "What it checks" are constant; the problem cells follow the rule given (G =
gates.json `gates`, V = that gate's `values`, R = gates.json `result`):

| Gate cell | What it checks | Problem cell |
|---|---|---|
| `Adopted arm` | `link, answer type and weighting; router type` | link display of R `link` (`identity`, `log(y + c)`, `arcsine`) + ", " + ("plain answers" if R `table_kind` == plain, "corrected answers" if corrector) + ", " + ("error-weighted" if R `weighted` is true, else "uniformly weighted") + "; " + ("per-location router" for per_unit, "region router" for region, "neighbour router" for neighbour) |
| `E1` | `engine code hash equals the run manifest's` | `passed` |
| `E2` | `library versions and Python equal the manifest's` | `passed` |
| `E0` | `the engine's RAM pre-flight predicts no refusal` | `passed`, or `passed (warning overridden)` when V `ignored` is true |
| `E3a` | `inputs, before the labels are read, equal the manifest's (dataset package, regions, constants, file lists, features)` | `passed` |
| `E3m` | `a moved dataset package file has the content, size and time that the run's locks record (path map)` | if G has `E3m_recorded_path_map`: "passed (" + COUNT(len(V `files`)) + (" file)" if that count is 1, else " files)"); else `not used (no moved file)` |
| `E3` | `dataset package fingerprint, the settings that the written rules set, and run fingerprint, after the written rules are applied` | `passed` |
| `E4` | `training rows: count and row-key hash` | "passed (" + COUNT(V `rows[0]`) + " rows)" |
| `E5ᵃ` | `bank fingerprint over every tree array (informational)` | `differs (informational)` |
| `E5a` | `arcsine arm only: its identity-link twin is bit-identical on every checked row` | if present: "passed (" + COUNT(V `pre_bit_equal`) + " of " + COUNT(V `rows_checked`) + " rows)" (stop unless `pre_bit_equal` and `arm_bit_equal` both equal `rows_checked`); else `not applicable` |
| `E6` | `c and the identity tolerances (one per link) equal the run's records` | `passed` |
| `E7` | `error-weighted arm only: the error-weight model equals its record` | `passed` if present, else `not applicable` |
| `E9` | `captured router coefficients reproduce the engine's kernel bit for bit` | if V `region_proof` is null: "passed (all " + COUNT(V `fits_captured`) + " fits)"; else "passed (all " + COUNT(V `fits_captured`) + " region fits; region proof on " + COUNT(V `region_proof.score_rows`) + " score rows and " + COUNT(V `region_proof.background_rows`) + " background rows)" (stop unless `region_proof` `answers_equal`, `eta_ours_equal` and `eta_store_equal` are true and `errors` is empty) |
| `E8` | `kept predictions, pre-clip and clipped, on every test row of every sampled location` | if V `bit_identical` is true: "bit-identical (" + COUNT(V `pre_bit_equal`) + " of " + COUNT(V `rows_checked`) + " rows)"; else COUNT(V `pre_bit_equal`) + " of " + COUNT(V `rows_checked`) + " rows bit-identical; the rest within the D8 tolerance (largest relative difference " + SCI2(V `max_rel_pre`) + ")" |
| `E10` | `exported trees and evaluator reproduce the engine's tree answers bit for bit, on one sampled location's router fit rows and test rows (forest loss: every sampled location; coral bleaching: one survey visit's router fit rows and test row)` | if V has `rows_x_trees`: "passed (" + COUNT(V `rows_x_trees[0]`) + " rows, " + COUNT(V `rows_x_trees[1]`) + " trees)"; else "passed (every sampled location of the " + COUNT(V `regions`) + " regions)" |

Notes (exact):

```
ᵃ E5 is informational: the rebuilt bank's fingerprint differs from the run's on all five problems, while every checked tree answer and prediction matches: bit for bit (E5a, E10, and E8 on the identity and log(y + c) arms), and within the D8 tolerance on the arcsine arms (E8); the cause is not established.
D8 (gate E8 on burned fraction and coral bleaching): a relative difference of at most 10⁻¹² on arcsine arms only (ruling AY3), licensed at this lead by gate E5a.
```

cells.json keys: row = gate id (`E3m`, `E4`, `E5a`, `E8`, `E9`, `E10`; the others print no number), column =
problem; parts: E3m `files` (version 2, G3: its selector is `len(gates.E3m_recorded_path_map.values.files)` and its
stored value the list's length); E4 `rows`; E5a `bit_equal`, `rows`; E8 `bit_equal`, `rows`, `max_rel` (D8 cells only);
E9 `fits`, `score_rows`, `background_rows`; E10 `rows`, `trees` or `regions`.

### 4.6 Table S3.22: the main-text row with its components

Caption line:

```
**Table S3.22 (post hoc).** The main-text row (Table 9) with its components, nowcast, variable level. From the comparison's output files, except the cells marked †. <!-- src: D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/compare/AW4_main_row.json; pairs.parquet (spearman_top20_union of treeroute v1 with each same-link rival); families.parquet (each same-link rival's own-history share); D:/treeroute/analysis/shap_v1/verify_v1/A/results.json problems.fire.main_row (the cells marked with a dagger, ruling BB1); rulings BB1, BB4, BB6 -->
```

Header:

```
| Quantity | PM2.5 | NDVI | Burned fraction | Forest loss | Coral bleachingᵈ |
|---|---|---|---|---|---|
```

Rows, in this order (exact first cell; then one cell per problem in the order of 2.1). "Rivals" means AW4
`models_in_main_set` without treeroute, in the display order of 2.2.

| Quantity cell | Problem cell (fire's cell in brackets where it differs) |
|---|---|
| `Link of the main set` | link display (2.3) of AW4 `reference_link` |
| `Main set` | AW4 `models_in_main_set` as a model list (fire: `treeroute v1 onlyᵃ`) |
| `Rivals in another link that passed their skill guard` | AW4 `cross_link_models` as a model list |
| `Rivals declined by their skill guard` | AW4 `declined_models` as a model list |
| `Kendall's W of the main set [95% CI]` | as Table 9's W cell (fire: `undefined`) |
| `Spearman of treeroute v1 with each same-link rival` | for each rival: inline name + " " + NUM2(pairs(p, variable, rival, treeroute, spearman_top20_union).value), joined by "; " (fire: `–`) |
| `Median of those [95% CI]` | CI2 of AW4 `treeroute_vs_same_link_rivals_median_spearman_top20_union` (`value`, `ci[0]`, `ci[1]`, `ci[2]`) (fire: `–`) |
| `Range (lowest to highest)` | NUM2(`range[0]`) + " to " + NUM2(`range[1]`) (fire: `–`) |
| `RBO with the rivals' consensus, p = 0.9 [95% CI]` | CI2 of AW4 `["rbo_vs_consensus_p0.9"]`, on pm25 + `ᵇ` (fire: `–`) |
| `treeroute v1's top 3` | AW4 `treeroute_top3` as a name list (fire: A's names as a name list + `†`) |
| `Consensus top 3` | AW4 `consensus_top3` as a name list (fire: `–`) |
| `Own-history share, treeroute v1 [95% CI]` | CI2 of AW4 `own_history_share_treeroute`, on coral + " (no own-history input)" (fire: CI2 of A's `own_history_share_treeroute` + `†`) |
| `Own-history share of each same-link rival` | for each rival: inline name + " " + NUM2(families.parquet `share` of (rival, `own history`)), joined by "; "; on coral the label " (no own-history input)" is appended once, at the end of the joined cell, not after each rival's share (version 2, G4) (fire: `–`) |
| `Own-history share, median of the rivalsᶜ [95% CI]` | CI2 of AW4 `own_history_share_median_rival`, on coral + " (no own-history input)" (fire: `–`) |

Notes (exact, in this order):

```
ᵃ Burned fraction: every rival explains in another link (LightGBM, the random forest and Ridge in log(y + c), the Tweedie booster in log μ), and Ridge also failed its skill guard, so the main set is treeroute v1 alone. W needs two models and is undefined, and the cells that need a rival are empty (–): agreement between treeroute v1 and a rival cannot separate the link from the model there.
ᵇ PM2.5: the interval of the RBO with the consensus is asymmetric because the consensus's top variable changes across the region draws.
ᶜ The median of the main-set rivals' own-history shares: on PM2.5 and forest loss LightGBM's share; on NDVI, with four rivals, the mean of the two middle shares.
ᵈ Coral bleaching's table of these statistics (AW4_table.md, written on 2026-11-13 at 00:06) was read on 2026-11-13 at about 15:31, before the independent re-computation; the re-computation's implementers A and B never opened it (ruling BB6; Supplement S1.7 records who read it).
† From the independent re-computation of the comparison (two implementations that agree): the comparison's output files leave these cells empty, because they are written only when treeroute v1 has a same-link rival (ruling BB1).
```

cells.json keys: row = `kendall_w`, `spearman_per_rival`, `spearman_median`, `spearman_range`, `rbo_vs_consensus`,
`own_history_treeroute`, `own_history_per_rival`, `own_history_median_rivals`; column = problem; parts `value`,
`ci_low`, `ci_high` (`n_finite` only when printed), for the per-rival rows the rival's data name, for the range
`min` and `max`.

### 4.7 Tables S3.23 to S3.27: the comparison per problem (AW3)

Table ids: S3.23 pm25, S3.24 ndvi, S3.25 fire, S3.26 defo, S3.27 coral. Each has panels a-f; fire and coral also g.

Caption line (one template; `{nn}` the table number, `{Problem}` the display name, `{p}` the data name):

```
**Table S3.{nn} (post hoc).** {Problem}, nowcast: agreement of the models' SHAP attributions, every pair at the variable level (a) and at the feature level (b); the main set's agreement and each model's stability (c); each model's top 10 at both levels (d, e) and its family shares (f){g_clause}. Link space. Percentile 95% intervals over 2,000 paired region draws, with the number of finite draws where a statistic is defined on 1 to 1,999 of them. Same-link pairs are comparable; cross-link pairs are shown for completeness and are not comparable in scale or rank. {shares_sentence} <!-- src: D:/treeroute/analysis/shap_v1/out/{p}/lead_0/compare/pairs.parquet, per_lead.json, importance.parquet and families.parquet; D:/treeroute/analysis/shap_v1/verify_v1/A/results.json problems.{p}.levels.<level>.pairs (the sign agreement's intervals, ruling BB1){extra_src}; rulings BB1, BB2{extra_rulings}, BB5 -->
```

- `{g_clause}`: fire and coral `; and the arcsine-link models' top 10 on their rows with a forecast above 0 (g)`;
  else empty.
- `{extra_src}`: ndvi `; D:/treeroute/analysis/shap_v1/verify_v1/_lead/outputs/bardl_maxima.txt (the spreads of the footnote, ruling BB3)`;
  else empty.
- `{extra_rulings}`: ndvi `, BB3`; defo and coral `, BB4`; else empty.
- `{shares_sentence}` (version 2, C1; version 3, V3-1): fire and coral (the tables with panel g)
  `Top-10 shares (d, e, g) are of a model's total mean absolute SHAP value over J (g: on its rows with a forecast above 0); family shares (f) are of the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; both means weight each region equally, and no share has an interval, as in the comparison's files.`;
  else (pm25, ndvi, defo)
  `Top-10 shares (d, e) are of a model's total mean absolute SHAP value over J; family shares (f) are of the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; both means weight each region equally, and neither share has an interval, as in the comparison's files.`

The two share bases (version 2, C1; as in 4.1): the top-10 shares of panels d and e (importance.parquet `share`) and
of panel g (PL `nonzero_forecast_rows`, on the model's rows with a forecast above 0) are of the model's total mean
absolute SHAP value over J; the family shares of panel f (families.parquet `share`) are of the sum of the model's five
families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values.
Both means weight each region equally, panel g's included (version 3, V3-1; PROTOCOL section 8, as in 4.1).
`{shares_sentence}` states both bases and the weighting in the caption.

**Panels a and b: every pair.** Label lines (exact):

```
**a. Variable level: every pair.**
```

```
**b. Feature level: every pair.**
```

Header of panel a (exact):

```
| Pair | Link | Spearman over J | Spearman, top-20 union | Kendall's tau-b | Jaccard top 5 | Jaccard top 10 | RBO, p = 0.9 | RBO, p = 0.95 | Share distance (TV) | Family-share distance (TV) | Sign agreement, top-10 union (signs)† |
|---|---|---|---|---|---|---|---|---|---|---|---|
```

Header of panel b: the same with `Family-share distance (TV)§` in place of `Family-share distance (TV)`, and, when
the feature level's `jaccard_top20` exists (check 3.3: defo and ndvi), one more column `Jaccard top 20` right after
`Jaccard top 10` (the separator then has 13 cells).

Rows: every unordered pair of PL `models`, sorted by (display rank of the earlier model, display rank of the later
model), the earlier model being the one with the lower display rank (2.2). Cells:

| Column | Statistic | Cell |
|---|---|---|
| Pair | - | the pair text of 2.2 (ndvi: `‡` appended when the pair contains rival_bardl_h1) |
| Link | - | from the pair's `pair_label` at that level (one label per pair and level, check 3.3): with M = "; raw model, declined by its guard: " (the source label's words, check 3.3) and P = "; raw model, declined by its skill guard: " (the printed words; version 3, V3-6), if the label holds M, the text before M + P + the inline names (2.2) of the data names after M (split on ", ") joined by ", "; else the label as it stands. So `cross-link (not comparable in scale or rank); raw model, declined by its guard: rival_ridge` prints `cross-link (not comparable in scale or rank); raw model, declined by its skill guard: Ridge` |
| Spearman over J | `spearman` | CI2(value, ci_low, ci_high, finite_replicates) |
| Spearman, top-20 union | `spearman_top20_union` | CI2 |
| Kendall's tau-b | `kendall_tau_b` | CI2 |
| Jaccard top 5 | `jaccard_top5` | CI2 |
| Jaccard top 10 | `jaccard_top10` | CI2 |
| Jaccard top 20 | `jaccard_top20` | CI2 (panel b of defo and ndvi only) |
| RBO, p = 0.9 | `rbo_p0.9` | CI2 |
| RBO, p = 0.95 | `rbo_p0.95` | CI2 |
| Share distance (TV) | `tvd` | CI2 |
| Family-share distance (TV) | `tvd_family` | CI2 of the VARIABLE-level row of the pair, in both panels (in panel b the same text as in panel a, ruling BB2) |
| Sign agreement | `sign_agreement_top10` | SIGN(value, signs_compared, A `ci_low`, A `ci_high`, A `n_finite`), A = `problems.{p}.levels.{L}.pairs["{a}|{b}"].sign_agreement` (check 3.4) |

**Panel c: agreement within the main set, and stability.** Label line and header (exact):

```
**c. Agreement within the main set, and each model's stability.**
```

```
| Statistic | Variable level | Feature level |
|---|---|---|
```

Rows, in this order: `Kendall's W of the main set [95% CI]`; `Mean pairwise Spearman of the main set [95% CI]`; then
one row per model of PL `models` in display order, first cell "Stability under region resampling: " + inline name.
Cells: W: CI2(PL `{L}.kendall_w_main_set` `value`, `ci[0]`, `ci[1]`, `finite_replicates`); mean Spearman: the same
with `mean_pairwise_spearman_main_set`; stability: NUM2(PL `{L}.stability_under_region_resampling.{model}`). On fire
the W and mean-Spearman cells are `undefinedᵃ` (value NaN, 0 finite).

**Panels d and e: top 10.** Label lines (exact):

```
**d. Variable level: each model's top 10 (share).**
```

```
**e. Feature level: each model's top 10 (share).**
```

Header: "| Rank | " + the header names (2.2) of PL `models` in display order joined by " | " + " |" (ndvi: `BARDL‡`
in place of `BARDL`), and the separator of that many columns. Rows `1` to `10`: cell = TOP(player, share) of the model's rank-k row in the
order of check 3.5 (`importance.parquet`, that level, `active` true). Last row: first cell `Nonzero variables` (panel
d) or `Nonzero players` (panel e), cells COUNT(PL `{L}.nonzero_players.{model}`).

**Panel f: family shares.** Label line and header (exact first cells):

```
**f. Family shares (sums of the variable-level attributions per row).**
```

Header: "| Family | " + the model header names in display order joined by " | " + " |" (no mark on BARDL here).
Rows in this order, first cells `Own history`, `Global indices`, `Local drivers`, `Context and calendar`, `Seasonal
normal` (families.parquet families
`own history`, `global indices`, `local drivers`, `context and calendar`, `seasonal normal`). Cell = PCT1(share), with
the label of 2.7 appended (one space) when the family has no variable in the problem.

**Panel g (fire and coral): rows with a nonzero forecast.** Label line (exact):

```
**g. Arcsine-link models, rows with a forecast above 0: top 10 (share).**
```

Header: "| Rank | " + the header names of the models that are keys of PL `nonzero_forecast_rows`, in display order,
joined by " | " + " |". Rows `1` to `10`: TOP(name, share) from PL `nonzero_forecast_rows.{model}.top10[k-1]` =
`[name, share]`, in the stored order. Last row: first cell `Rows with a forecast above 0`, cells COUNT(PL `nonzero_forecast_rows.{model}.rows`).

**Notes**, in this order (exact; lines marked "fire", "ndvi", "fire and coral" appear only in those tables):

fire:

```
ᵃ The main set is treeroute v1 alone: every rival explains in another link, and Ridge also failed its skill guard. Kendall's W and the mean pairwise Spearman need two models and are undefined; agreement between treeroute v1 and a rival cannot separate the link from the model.
```

all five:

```
Sign agreement: of the players in the union of the two top-10 sets whose sign is determined in both models (the bootstrap 95% interval of the signed mean excludes 0), the share whose signs agree; in brackets, the number of such players ("signs") and, where the statistic is defined on 1 to 1,999 of the 2,000 draws, that number of draws. Undefined: no player qualifies on the full sample; printed without an interval, it is undefined on every draw.
† The sign agreement's interval is from the independent re-computation of the comparison (two implementations, A and B, that agree; ruling BB1): the comparison script evaluates the sign agreement on the full sample only, so its files hold no interval. The value and its number of signs are the comparison's.
```

ndvi (one line; placeholders below):

```
‡ BARDL reads three variables (nine columns) by design and gives exactly 0 to the other {z_var} of the {j_var} variables of J ({z_feat} of the {j_feat} players at the feature level). Beyond its three variables (variable level) and nine columns (feature level), its ranking is therefore filled by name order, the tie rule applied in code-point ascending order, and so are its top-5, top-10 and top-20 sets where they reach that far; the cells of its pairs that read that part of its ranking (the Jaccard similarities, the top-20-union Spearman and the RBO) depend on that order. Across the three orders tried (code-point ascending, as printed; case-insensitive ascending; and descending), the largest spread (highest minus lowest value) of each statistic over BARDL's eight pair-levels is: Jaccard top 5, {m_jaccard_top5} ({at_jaccard_top5}); Jaccard top 10, {m_jaccard_top10} ({at_jaccard_top10}); Jaccard top 20, {m_jaccard_top20} ({at_jaccard_top20}); top-20-union Spearman, {m_rho20} ({at_rho20}); RBO p = 0.9, {m_rbo090} ({at_rbo090}); RBO p = 0.95, {m_rbo095} ({at_rbo095}). For example, BARDL's Jaccard top 5 with treeroute v1 at the variable level is {ex_base} with the tie-only `aet_total_mm` in its top 5, and {ex_desc} without it (ruling BB3).
```

all five:

```
§ Families are sums of variable-level attributions, so at the feature level the family-share distance is the variable-level value repeated (ruling BB2).
Stability (panel c): the mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement. Nonzero (panels d and e): the players of J to which the model gives a nonzero share.
```

fire and coral:

```
Panel g: each arcsine-link model's variable-level shares on its rows with a forecast above 0, over every variable of the problem, in the comparison file's order.
```

Placeholders of the ndvi note: `{j_var}` = COUNT(PL `variable.active`); `{z_var}` = COUNT(PL `variable.active` −
PL `variable.nonzero_players.rival_bardl_h1`); `{j_feat}`, `{z_feat}` the same at the feature level; for each of the
six statistics s of section 1's maxima block (`jaccard_top5`, `jaccard_top10`, `jaccard_top20`, `rho20`, `rbo090`,
`rbo095`): `{m_s}` = NUM2(float(spread text)), `{at_s}` = ("variable level" or "feature level", from the level field)
+ ", " + the pair text of 2.2 of the pair key's two models (without `‡`; for example `treeroute v1 vs BARDL`);
`{ex_base}` = NUM2(float(first value text of the jaccard_top5 line)), `{ex_desc}` = NUM2(float(third value text of
that line)).

cells.json keys: panels a and b: row = the pair key `{a}|{b}` (data names in Python string order), column = the
statistic name (`spearman`, ..., `tvd_family`, `sign_agreement_top10`), parts `value`, `ci_low`, `ci_high`,
`n_finite` (when printed), `signs` (sign agreement). In panel b the `tvd_family` entries name the variable-level row
in their selector. Panel c: rows `kendall_w`, `mean_pairwise_spearman`, `stability:{model}`, columns `variable`,
`feature`. Panels d, e, g: rows `rank_1` to `rank_10` (part `share`) and `nonzero` or `rows` (part `count`),
column = model data name. Panel f: row = family name (as in families.parquet), column = model, part `share` (version
2, G1: as the other shares printed without an interval). Note numbers (ndvi):
row `note`, columns `z_var`, `j_var`, `z_feat`, `j_feat`, `m_{s}`, `ex_base`, `ex_desc`, part `number`; `z_var` and
`z_feat` store `[active, nonzero]` and have the selector `variable.active - variable.nonzero_players.rival_bardl_h1`
(feature likewise).

### 4.8 Table S3.28: B1, the pair (main run, B1 run)

Caption line:

```
**Table S3.28 (post hoc; sensitivity).** treeroute v1's B1 sensitivity, nowcast: the pair (main run, B1 run) at the variable level (a) and the feature level (b). B1 explains the same 1,000 sample rows against all of each location's router fit rows at or before the cut, not only those of the same calendar month (B2), so the month and the seasonal normal can take credit. treeroute v1 only; B1 is never pooled with the main set: it enters no Kendall's W, consensus or main-text row and is compared with no rival. J is the pair's own (the players to which either run gives more than 10⁻¹² of its total), so Spearman over J, Kendall's tau-b and RBO are not read against the main pairs' values number for number. Every number is from the independent re-computation (two implementations that agree); percentile 95% intervals over the problem's 2,000 saved region draws; counts without intervals. Coral bleaching: B1 is not defined; forest loss: the identity check of Table S3.30. <!-- src: D:/treeroute/analysis/shap_v1/verify_v1/A/results.json b1.<problem>.<level>.pair_main_b1 and b1.<problem>.<level>.importance.n_nonzero; rulings BA3, BB2 -->
```

Label lines (exact):

```
**a. Variable level: the pair (main run, B1 run).**
```

```
**b. Feature level: the pair (main run, B1 run).**
```

Header (both panels):

```
| Statistic | PM2.5 | NDVI | Burned fraction |
|---|---|---|---|
```

Columns: pm25, ndvi, fire. Rows, in this order (exact first cells; `B` = A `b1.{p}.{L}`, `Q` = `B.pair_main_b1`):

| First cell | Cell |
|---|---|
| `Variables in the pair's J` (a) / `Players in the pair's J` (b) | COUNT(Q `n_J.value`) |
| `Nonzero in the B1 run` | COUNT(B `importance.n_nonzero.value`) |
| `Spearman over J` | CI2(Q `spearman_J` value, ci_low, ci_high, n_finite) |
| `Spearman, top-20 union` | CI2 of Q `spearman_top20_union` |
| `Kendall's tau-b` | CI2 of Q `kendall_tau_b` |
| `Jaccard top 5` | CI2 of Q `jaccard_top5` |
| `Jaccard top 10` | CI2 of Q `jaccard_top10` |
| `Jaccard top 20` | panel b only: CI2 of Q `jaccard_top20` when it is an object, `–` when it is null (the panel a row is left out because all three are null; generally: this row appears in a panel exactly when at least one of its three cells is an object) |
| `RBO, p = 0.9` | CI2 of Q `rbo_p090` |
| `RBO, p = 0.95` | CI2 of Q `rbo_p095` |
| `Share distance (TV)` | CI2 of Q `tv_shares` |
| `Family-share distance (TV)` (a) / `Family-share distance (TV)§` (b) | CI2 of A `b1.{p}.variable.pair_main_b1.tv_family_shares` in both panels (ruling BB2) |
| `Sign agreement, top-10 union` | CI2 of Q `sign_agreement` |
| `Signs determined in both runs / of those, agreeing` | COUNT(Q `sign_n_determined.value`) + " / " + COUNT(Q `sign_n_agree.value`) |

Notes (exact):

```
–: not defined, because the pair's J has fewer than 200 players (the top-20 Jaccard is given only from 200 players).
§ Families are sums of variable-level attributions, so at the feature level the family-share distance is the variable-level value repeated (ruling BB2; an exception to the rule that B1's numbers follow the main comparison's choices).
```

cells.json keys: row = A's key name (`n_J`, `n_nonzero`, `spearman_J`, `spearman_top20_union`, `kendall_tau_b`,
`jaccard_top5`, `jaccard_top10`, `jaccard_top20`, `rbo_p090`, `rbo_p095`, `tv_shares`, `tv_family_shares`,
`sign_agreement`), and `sign_counts` for the last row (parts `determined`, `agree`); column = problem; parts `value`,
`ci_low`, `ci_high` (`n_finite` only when printed), `count` for `n_J` and `n_nonzero`. In panel b the
`tv_family_shares` entries name the variable-level path in their selector.

### 4.9 Table S3.29: B1, the B1 run's family shares, top 3 and top 10

Caption line:

```
**Table S3.29 (post hoc; sensitivity).** treeroute v1's B1 run, nowcast: family shares [95% CI] (a), top 3 and own-history share (b), and top 10 at both levels (c, d; no interval for a top-k list). Top-3 and top-10 shares are of the B1 run's total mean absolute SHAP value over the pair's J; family shares and the own-history share are of the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; both means weight each region equally. From the independent re-computation (two implementations that agree). <!-- src: D:/treeroute/analysis/shap_v1/verify_v1/A/results.json b1.<problem>.variable.families, b1.<problem>.variable.top3, b1.<problem>.variable.own_history_share, b1.<problem>.<level>.top10; rulings BA3, BB5 -->
```

Panels (label lines exact; header `| {first} | PM2.5 | NDVI | Burned fraction |` with `{first}` given; columns
pm25, ndvi, fire):

```
**a. Variable level: the B1 run's family shares [95% CI].**
```

First header cell `Family`. Rows `Own history`, `Global indices`, `Local drivers`, `Context and calendar`, `Seasonal
normal`: CIP(A `b1.{p}.variable.families.{f}` value, ci_low, ci_high, n_finite) for f = `own_history`,
`global_indices`, `local_drivers`, `context_and_calendar`, `seasonal_normal` (label of 2.7 never applies here: these
problems have a variable in every family).

```
**b. Variable level: the B1 run's top 3 and own-history share.**
```

First header cell `Quantity`. Rows: `Top 3 (share)`: TOP(name, share) of the A `b1.{p}.variable.top3` entries, in
their stored order, joined by ", "; `Own-history share [95% CI]`: CI2 of A `b1.{p}.variable.own_history_share` (the
main-text row's form).

```
**c. Variable level: the B1 run's top 10 (share).**
```

```
**d. Feature level: the B1 run's top 10 (share).**
```

First header cell `Rank`. Rows `1` to `10`: TOP(A `b1.{p}.{L}.top10[k-1]`).

The two share bases (version 2, C1; as in 4.1): B1's top-3 and top-10 shares (A `b1.{p}.variable.top3`,
`b1.{p}.{L}.top10`) are of the B1 run's total mean absolute SHAP value over the pair's J; its family shares and its
own-history share (A `b1.{p}.variable.families`, `b1.{p}.variable.own_history_share`) are of the sum of its five
families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values.
Both means weight each region equally, as in the main runs (version 3, V3-1; PROTOCOL section 8, as in 4.1); the
caption says so.

Notes (exact):

```
Under B1 the month and the seasonal normal can take credit; under B2 they are exactly 0 on these three problems. The own-history share is the own-history family's share. Each B1 player's importance, share and signed mean, with its interval, is in the re-computation's results file (verify_v1/A/results.json, key b1).
```

cells.json keys: panel a row = family key, panel b rows `top3` (parts `share_1` to `share_3`) and
`own_history_share`, panels c and d rows `rank_1` to `rank_10` (part `share`); column = problem.

### 4.10 Table S3.30: B1, run facts and forest loss's identity check

Caption line:

```
**Table S3.30 (post hoc; sensitivity).** treeroute v1's B1 runs: background pairs and seconds, from each run's log (a), and forest loss's identity check (b). Forest loss is annual, so its B1 background equals its main run's, and its B1 run must repeat the main run exactly. <!-- src: D:/treeroute/analysis/shap_v1/logs/tr_shap_<problem>_lead0.log (the B1 run's set-up and "done in" lines); D:/treeroute/analysis/shap_v1/verify_v1/A/results.json b1.defo.identity; rulings BA3 -->
```

Panel a (label and header exact):

```
**a. Background pairs and seconds of each B1 run, from its log.**
```

```
| Problem | Background pairs | Total seconds | Tree-SHAP seconds |
|---|---|---|---|
```

Rows pm25, ndvi, fire, defo (display names). The B1 block of a log: read the file as section 1's text formats say
(universal newlines, encoding `utf-8-sig`; version 2, G2) and split the text on `\n`; the set-up lines match

```
^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] (\w+) lead 0: (\d+) rows, (\d+) background pairs,
```

(used with `re.match`, so the rest of the line is free; group 1 the time, 2 the problem, 3 the rows, 4 the pairs);
the B1 set-up line is the LAST set-up line of the file (stop if its
time is before `2026-11-15 23:06:00`, its problem is not `<p>` or its rows are not 1000). The "done in" line is the
first line after it that matches, as a line without its line end (G2),

```
^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] treeroute SHAP (\w+) lead 0 done in ([0-9.]+) s \(tree SHAP ([0-9.]+) s\)$
```

(group 3 the total seconds, 4 the tree-SHAP seconds). Cells: COUNT(int(pairs text)); SECS(float(total text));
SECS(float(tree text)) (check 3.8).

Panel b (label and header exact):

```
**b. Forest loss: the B1 run against the main run.**
```

```
| Check | Result |
|---|---|
```

Rows (exact first cells; `I` = A `b1.defo.identity`):

| First cell | Result |
|---|---|
| `Largest absolute difference of the SHAP values, feature level (every row and player)` | SCI2(I `max_abs_diff_phi`) |
| `Largest absolute difference of the SHAP values, variable level (every row and variable)` | SCI2(I `max_abs_diff_phiv`) |
| `Rows, main run / B1 run` | COUNT(I `n_rows_main`) + " / " + COUNT(I `n_rows_b1`) |
| `Players, main run / B1 run` | COUNT(I `n_players_main`) + " / " + COUNT(I `n_players_b1`) |
| `Variables, main run / B1 run` | COUNT(I `n_variables_main`) + " / " + COUNT(I `n_variables_b1`) |
| `Same rows / players / variables` | each of I `same_rows`, `same_players`, `same_variables` as `yes` (true) or `no` (false), joined by " / " |

Notes (exact):

```
Coral bleaching: B1 is not defined, so it has no B1 run.
The identity check matches rows by their sample row and players and variables by name; it is from the independent re-computation (two implementations that agree), and it held exactly, so the B1 numbers of PM2.5, NDVI and burned fraction are reported (Tables S3.28 and S3.29).
```

cells.json keys: panel a row = problem, columns `pairs`, `total_seconds`, `tree_shap_seconds`; panel b rows
`max_abs_diff_phi`, `max_abs_diff_phiv`, `rows`, `players`, `variables` (parts `main`, `b1`), column `result`.

---

## 5. cells.json

One JSON document, a dict with three keys in this order: `tables_file` with the text `tables.md`; `spec` with the
text `OUT\spec\TABLE_SPEC.md` (written by json as `"OUT\\spec\\TABLE_SPEC.md"`); `entries`, the list of entries
below. It is written by `json.dumps(doc, ensure_ascii=False, indent=1, allow_nan=False) + "\n"` (UTF-8, no BOM; no
other formatting step). `tables_file` names the builders' `tables.md` (`OUT\<X>\tables.md`, beside cells.json), of
which `OUT\reconcile\tables_agreed.md` is a byte copy with the same lines, so an entry's `line` is the same line in
both files (version 3, V3-7).

One entry per printed data number, and one per printed `undefined` that stands for a number (section 2.7). Constant
numbers of the fixed texts (captions, headers, notes without placeholders, panel b of Table S3.18) are not entries;
the checks of section 3 hold them to the data. Entries are in reading order of tables.md: by line, and within a
line from left to right.

Entry (keys in this order):

| Key | Value |
|---|---|
| `line` | the 1-based line number of tables.md on which the number is printed |
| `table` | `9` or `S3.18` ... `S3.30` |
| `panel` | `a` ... `g`, or `""` for a table without panels or for a note |
| `row` | the row key of section 4 (`note` for a number in a note) |
| `column` | the column key of section 4 |
| `part` | the part name of section 4 (`value`, `ci_low`, `ci_high`, `n_finite`, `signs`, `count`, `share`, ...). Where section 4 names no part (version 2, G1): a cell that prints one number uses `value`; the family shares of panel f in Tables S3.23-S3.27 use `share`, as the other shares printed without an interval (panels d, e and g; Table S3.29 c and d); an interval cell uses `value`, `ci_low`, `ci_high`, and `n_finite` when it is printed |
| `printed` | the exact printed token (`0.85`, `−0.08`, `1,140`, `7.1%`, `<0.1%`, `2.1 × 10⁻¹⁴`, `undefined`) |
| `cell` | the exact full text of the cell (or of the note line) that holds it, marks included |
| `source` | the short path of the file read, with backslashes (`SHAP\out\pm25\lead_0\compare\pairs.parquet`, `V\A\results.json`, `SHAP\rebuild\fire\lead_0\gates.json`, `SHAP\logs\tr_shap_fire_lead0.log`, `SHAP\SAMPLE_REGISTER.txt`, `SHAP\sample\fire\sample_manifest.json`, `V\_lead\outputs\bardl_maxima.txt`) |
| `selector` | how the value was found (grammar below) |
| `stored` | a list of the stored values the number came from, as read: a parquet float64 as a Python float, an int64 as an int (numpy scalars converted with `.item()`), JSON numbers as parsed, log and register numbers as `int(text)` or `float(text)`; NaN or null as `null` |

Selector grammar:

- parquet: the key terms `name=value` of the file's key columns, joined by "; ", then "; column=" + the column
  read. Key columns: pairs.parquet `level`, `model_a`, `model_b`, `statistic`; importance.parquet `level`, `model`,
  `player`; families.parquet `model`, `family`. Examples:
  `level=variable; model_a=rival_lgbm; model_b=treeroute; statistic=spearman; column=value`,
  `level=variable; model=treeroute; player=hist_last; column=share`, `model=treeroute; family=own history; column=share`.
- JSON: a path whose segments are `.name` for a key matching `^[A-Za-z_][A-Za-z0-9_]*$` (no dot before the first),
  `["key"]` for any other key (JSON string escaping), `[i]` for a list index. Examples: `kendall_w.ci[0]`,
  `["rbo_vs_consensus_p0.9"].value`, `variable.stability_under_region_resampling.rival_lgbm`,
  `problems.fire.levels.variable.pairs["rival_lgbm|treeroute"].sign_agreement.ci_low`,
  `gates.E8_predictions.values.max_rel_pre`, `background_rows["0"].min`, `nonzero_forecast_rows.treeroute.top10[2][1]`.
  A derived count: `len(<path>)` or `<path> - <path>`.
- log, register, maxima text: `line <n>: <field>` with the 1-based line number in that file (counted on the lines read
  as section 1's text formats say: universal newlines, `utf-8-sig`; version 2, G2) and the field name
  (`background pairs`, `total seconds`, `tree SHAP seconds`, `n`, `spread`, `value 1`, `value 3`).

---

## 6. Decisions (presentation choices left open by the protocol, the rulings and the brief)

1. **Numbering and order.** Table 9 in the main text; S3.18-S3.30 in the order of 4: first what was explained and how
   it was checked (S3.18-S3.21), then the results (S3.22 main row in full, S3.23-S3.27 one AW3 table per problem),
   then B1 apart (S3.28-S3.30). Why: S3's sections run "when and why, method, result", and protocol section 10
   defines the AW3 table per problem-lead as holding the pairs at both levels, the top 10s, the family shares and the
   nonzero view, so each problem's table holds all of them as panels.
2. **Problem order and names.** PM2.5, NDVI, burned fraction, forest loss, coral bleaching, with the glossary's names
   ("fire" and "defo" are banned in the text). Why: the order of Tables 1, 4a, 4b and 6.
3. **Model order and names.** treeroute v1, then Table 6's rival order (Ridge, random forest, LightGBM, Tweedie
   booster, absolute-error booster), then BARDL; glossary and Table 3 names; the data names appear once, in Table
   S3.18. Pairs are sorted by this order, so treeroute v1's pairs come first. Why: consistency with the paper's rival
   tables; the treeroute pairs are the ones Table 9 summarises.
4. **Formats.** Statistics with two decimals and their intervals in brackets, as compare_shap's printouts; shares in
   percent with one decimal; the main row's own-history shares as fractions with two decimals (ruling BB4 fixes
   "0.00 [0.00, 0.00]" for that row); counts with thousands separators; check magnitudes as "2.1 × 10⁻¹⁴" (the
   supplement's style, for example Table S3.7); B1 in the same formats as the main pairs (it is the same statistics).
   Changes from the printouts and why: the Unicode minus (every table of the drafts uses it); no plus sign (plus is
   reserved in the paper for signed contrasts d, which these are not); "1 sign" in the singular; `undefined` in place
   of `nan`; a positive share below 0.05% prints `<0.1%`, so that a tiny positive share (for example a B1 family) is
   never shown as the structural 0.0% of B2.
5. **Rounding.** Python's `format()` on the stored double (correct rounding of the binary value, ties to even), one
   call per number. Why: compare_shap's printouts use it, the data hold exact binary ties (0.625), and only one
   stated rule makes two builders byte-identical.
6. **Finite replicates.** Printed only when fewer than the 2,000 draws, for every interval (in these data that happens
   for three of fire's sign-agreement intervals only, ruling BB1). Why: section 8 asks for each interval's finite
   count; printing 2,000 in some 900 cells adds nothing.
7. **Undefined and empty.** `undefined` for a statistic that has no finite value on the full sample, with its interval
   when draws give one; `–` for a cell that does not apply. Why: the two cases mean different things (fire's W is
   computed and undefined; fire's rival cells have no rival).
8. **BB1 marks.** `†` on the sign-agreement column header of every AW3 pair panel and on fire's two main-row cells
   (Table 9, Table S3.22); a note under each says that these numbers come from the re-computation (A = B) and why the
   comparison's files lack them. The sign agreement's value and its count are taken from pairs.parquet, only its
   interval and finite count from `V\A\results.json`, because protocol section 9 takes from the re-computation only the
   numbers compare_shap.py does not write; check 3.4 holds the two sources equal where both hold a number. The B1
   tables carry no † because every B1 number is the re-computation's, as their captions say.
9. **BB2.** The feature-level panels and the B1 feature panel carry a "Family-share distance (TV)§" column or row
   whose cells repeat the variable-level cells exactly, with the § note.
10. **BB3.** `‡` on the Pair cell of every NDVI pair with BARDL (both levels) and on BARDL's header in NDVI's top-10
    panels; one footnote with the counts from per_lead.json and the six largest spreads over the three collations and
    the example from bardl_maxima.txt, each rounded once to two decimals, the precision of the cells it qualifies.
11. **BB4.** The empty-family label is appended to the 0 in each cell (Table 9, Table S3.22 and the family panels),
    not put in the row name, so that every printed 0 of such a family carries it. One column label "median of the
    rivals" with a note naming what it is on PM2.5, forest loss and NDVI (checked against the data, 3.7). The PM2.5
    RBO note is under Table 9 and Table S3.22, the two tables that print that interval.
12. **BB5.** No interval for the main models' top-10 shares and family shares; the captions say so ("neither share
    has an interval, as in the comparison's files", or "no share has an interval" in the two tables with panel g;
    version 3, V3-1). B1's family shares and own-history share keep their intervals; no top-k list has one.
13. **BB6.** The disclosure is note ᵈ of Table S3.22, the table that prints what coral's AW4_table.md held.
14. **Main row in full (S3.22).** Rows are quantities, columns problems, so that the components of the median, range
    and median of the rivals (each same-link rival's top-20-union Spearman and own-history share) stand next to them.
    The consensus's own shares are not printed: no comparison file holds them.
15. **Structural zeros** are listed by name under Table S3.19 (one line per problem), not in each AW3 table, which
    keeps the AW3 tables to the statistics.
16. **Jaccard top 20** is a column only in the panels where it is defined (defo and ndvi, feature level), as in the
    printouts; in the B1 feature panel it is a row with `–` for the two problems whose pair J is under 200.
17. **Sample table (S3.19)** adds the frame rows and the background size per sample row from the sample manifest, and
    the background pairs from treeroute's meta.json, so that "rows, regions and units" are read with what they are
    drawn from and explained against.
18. **Checks tables.** S3.20 per model (S-EXACT with both columns where a loader checked both, additivity at both
    levels, S-ZERO, the four stop rules, the guard); S3.21 per gate, in the protocol's running order, with the adopted
    arm as the first row. treeroute's E8 numbers appear in both, from the same record, with the same text.
19. **B1 per-player vectors** (each B1 player's I, share and signed mean with intervals) are not printed; a note points
    to the results file. Why: S3.13 prints no model's full vector (the main models' are in importance.parquet), and
    they would add some 980 rows; the brief's item 9 lists the top 10 with shares.
20. **B1 run facts** come from the B1 block of each log (its last set-up line and the next "done in" line), with
    A's, meta.json's and the done record's values as checks (3.8).
21. **Data names in backticks** in every table, Table 9 included. Why: S2's tables print column names that way, and
    backticks keep the double underscores and colons of the feature names literal in the Word build.
22. **Source comments** follow the drafts' convention (paths relative to the research folder or `D:/treeroute/...`;
    fact IDs do not exist yet for these numbers), and contain no `--`.

---

## 7. Questions for the owner

None. Rulings BB1-BB6 settle the presentation; the remaining choices are presentation only and are listed in section 6.

---

## 8. What the spec writer opened

- Read: the brief; `SHAP\PROTOCOL.md` in full; `ROOT\engine\OWNER_RULINGS_2026-10-06.md` sections AW to BB;
  `SHAP\RUN_COMMANDS.md`; `V\reconcile\report.md` (fourth version: the lead's note, sections 1-6 and the addendum
  A1-A6, the first rows of A7); the ten printouts `AW3_table.md` and `AW4_table.md` of the five problems (formats only);
  `AW4_main_row.json` and `per_lead.json` of the five problems; `V\spec\SPEC.md`; `V\_lead\outputs\bardl_maxima.txt`
  and `bardl_ties.txt`; `V\_lead\scripts\bardl_maxima.py`, `bardl_ties.py` and `b1_tables.py` (read, not run); the five
  rebuild `gates.json`; `SHAP\SAMPLE_REGISTER.txt` and the five `sample_manifest.json`; the four treeroute SHAP logs and
  coral's; `ROOT\engine\PENDING_PARTS.md` Part 628; `ROOT\paper\draft\S3_posthoc.md` (header, S3.0-S3.2, S3.6-S3.12),
  `GLOSSARY.md`, `TABLE_NUMBERS.md`, `tables\table_7.md`, `tables\table_6.md`, the problem order of `table_1.md`,
  `table_3.md` and `table_5.md`, Table 3 of `03_protocol.md`, and `ROOT\paper\build\BUILD_README.md`; two lines of
  `S2_ban_counts.md` (backticked column names).
- Helper scripts in `OUT\spec\` (read-only, print only; their outputs went to the session's temporary folder):
  `s01_compare_schemas.py` (schemas and row counts of the compare files, with a few rows of each and families.parquet
  in full), `s02_results_tree.py` (key tree of `V\A\results.json`, the sign-agreement objects, fire's main row, the B1
  status and run objects, A's choices), `s03_run_records.py` (the run records' fields), `s04_edge_scan.py` (the facts
  of section 3 and the formatting edge cases: no top-10 order difference against A, no tied nonzero importance, two
  exact ties at 0.625, no negative zero), `s05_check_fields.py` (every field this spec names for Tables S3.18-S3.21 and
  S3.30, the log blocks), `s06_check_rules.py` (checks 3.1, 3.3, 3.5-3.7, 3.9 and 3.10 as worded here: 455 checks,
  0 failed).
- A throwaway prototype of a dozen cells (the format functions' self-test vectors, fire's sign-agreement cells, the
  four main rows, two E8 cells, fire's B1 family shares and top 3) ran from the session's temporary folder and is not
  kept in OUT, so that the builders' code stays independent of the spec writer's.
- One slip: a Grep with the glob `**/compare/AW*_table.md` over `SHAP\out` (searching for "-0.00"), which the brief's
  rule against `*.md` patterns over SHAP forbids. It could reach only the ten printouts the spec writer may read, and
  it matched nothing, so no line was shown.
- Not opened: any `rows.parquet`, `background_keys.parquet`, `V\B\`, `SHAP\smoke\bardl_fix\`; `bootstrap_stats.parquet`
  only by s01 (columns, row count, three rows). No script of `SHAP\scripts`, `V` or `V\_lead\scripts` was run.

---

## 9. Version 2 (2026-11-17)

Version 2 applies the change order `OUT\_brief\fix_order_v2.md`, written after the first check of version 1
(`OUT\reconcile\tables_agreed.md`, SHA-256 5f414a11...beae03): wording only; no number changes. Version 1 is kept byte
for byte as `OUT\spec\TABLE_SPEC_v1.md` (SHA-256 979be5ed...7cf9fb). `OUT\spec\CHANGES_v2.md` gives each change's
lines before and after, its OLD and NEW text and what a builder does differently; `OUT\spec\s07_diff_v1_v2.py`
confirms that every changed line belongs to a change listed here, and `OUT\spec\s10_check_new_texts.py` that the texts
below print the order's NEW texts. No fenced block was added or removed (63 in both versions); the notes block of
Table S3.18 (block 16) has a new first line. Line numbers below are those of version 2.

- C1, the two share bases: Table 9's caption (4.1, line 416) and a paragraph on the bases (lines 446-452); the S3.23 to
  S3.27 caption template's new placeholder `{shares_sentence}` (4.7, line 752), its two values (lines 760-763) and a
  paragraph (lines 765-769); the S3.29 caption (4.9, line 980) and a paragraph (lines 1013-1016); decision 12 (lines
  1191-1193).
- C2, the rivals' SHAP script: S3.20 notes ᵃ and ᵇ (4.4, lines 637-638); check 3.2 (line 337).
- C3, the BARDL footnote: the ‡ note (4.7, line 883); "spreads" in 2.8 (line 284) and decision 10 (lines 1185-1186).
- C4, rivals left out and coral's B1: Table S3.18 panel b without the CRW Outlook row and with the baselines row
  reworded (4.2, line 526); a new first note line (line 532); the S3.30 note (4.10, line 1090).
- C5: the S3.22 row label `Guard-passing rivals in another link` (4.6, line 717).
- C6: E10's "What it checks" (4.5, line 681) and note ᵃ of S3.21 (line 686).
- C7: the sign-agreement note of S3.23 to S3.27 (4.7, line 876).
- C8: note ᵈ of S3.22 (4.6, line 736).
- C9: the header comment (2.9, line 309).
- G1, cells.json part names: the rule in section 5 (line 1120); panel f's part `share` (4.7, lines 912-913).
- G2, source text formats: a paragraph in section 1 (lines 100-105); the log reading of 4.10 (lines 1046-1047 and
  1056); the selector grammar of section 5 (lines 1140-1141).
- G3: the E3m selector and stored value (4.5, lines 691-692).
- G4: coral's label in S3.22's "Own-history share of each same-link rival" (4.6, line 727).
- S9: this section, and its entry in the contents line (line 15).
- Left as in version 1 because the order does not name them: the S3.24 caption's source comment (`{extra_src}`, line
  757) still says "the collation moves of the footnote"; the S3.23 to S3.27 caption still says "with the number of
  finite draws where a statistic is defined on fewer of them"; the S3.18 caption's source comment names PROTOCOL
  sections 5 and 7 and Part 628, not the paper's Section 3.3 and Tables 4a and 7 that the reworded panel b rests on.
- Helper scripts of version 2 in `OUT\spec\` (read-only, print only): `s08_source_checks.py` (the order's claims
  against its sources), `s09_builder_cells_diff.py` (the two version-1 builders' cells.json files differ only in the
  part name of panel f's 125 family shares), `s11_cells_on_changed_lines.py` (the cells.json entries on changed lines),
  `s12_check_changes_file.py` (every text quoted in CHANGES_v2.md against the file it is quoted from).
- Opened for version 2: the order, the brief, version 1 and `tables_agreed.md`; `SHAP\PROTOCOL.md` sections 4.1, 5, 6,
  7 and 8 and part of 4.2;
  `ROOT\paper\draft\tables\table_6.md` (Table 7), `table_3.md` (Table 4a), `03_protocol.md` Section 3.3 and
  `S1_disclosures.md` section S1.7; `OUT\_brief\brief_text.md` (its S1 and AI-term items); the five rebuild
  `gates.json`; each problem's `families.parquet`, `importance.parquet` and `per_lead.json`; PM2.5's `rival_ridge`
  `exactness.json` and `ridge_shap_exactness.json`; `SHAP\SAMPLE_REGISTER.txt`, the five logs and `bardl_maxima.txt`
  (bytes and line ends; lines 1-7 of the maxima); `OUT\A\cells.json` and `OUT\B\cells.json` (and the SHA-256 of the
  two builders' tables.md).

---

## 10. Version 3 (2026-11-17)

Version 3 applies the change order `OUT\_brief\fix_order_v3.md`, written after the second check of version 2
(`OUT\reconcile\tables_agreed.md`, SHA-256 a7710171...6570c9, a byte copy of both builders' tables.md): wording
only; no number changes, and tables.md keeps its 785 lines. Version 2 is kept byte for byte as
`OUT\spec\TABLE_SPEC_v2.md` (SHA-256 2046c58a...ad30f02); version 1 stays `OUT\spec\TABLE_SPEC_v1.md`.
`OUT\spec\CHANGES_v3.md` gives each change's lines before and after, its OLD and NEW text and what a builder does
differently; `OUT\spec\s13_diff_v2_v3.py` confirms that every changed line belongs to a change listed here, and
`OUT\spec\s14_check_new_texts.py` that the texts below print the order's NEW texts. No fenced block was added or
removed (63 in both versions). Two blocks have a new first line, so a builder that finds a block by the start of its
first line uses the new one: the panel b label of Table S3.18 (block 14, now
`**b. Rivals and naive baselines left out.**`) and the notes of Table S3.18 (block 16, now starting
`Panel b lists the nowcast's rivals`). Line numbers below are those of version 3.

- V3-1, the region weighting and Table 9's families: Table 9's caption (4.1, line 417: the new importance sentence,
  the RBO's "importance shares", and the own-history share with the five families) and the paragraph on the two bases
  (lines 453-459); the S3.19 caption (4.3, line 551); the `{shares_sentence}` bullet and its two values (4.7, lines
  767-770) and the 4.7 paragraph (lines 776-777); the S3.29 caption (4.9, line 988) and the 4.9 paragraph (lines
  1025-1026); decision 12 (lines 1203-1205).
- V3-2, the naive baselines and references of Table S3.18: the caption and its source comment (4.2, line 480); the
  panel b label (line 520, block 14); the baselines row (line 533); the first note line (line 539, block 16).
- V3-3: the count clause of the S3.23-S3.27 caption template (4.7, line 759); `{extra_src}` (line 764).
- V3-4: the NDVI footnote (4.7, line 891); the meaning of `‡` (2.8, line 284).
- V3-5: the S3.22 row label `Rivals in another link that passed their skill guard` (4.6, line 724).
- V3-6: treeroute's skill-guard cell in S3.18 a (4.2, line 502) and in S3.20 (4.4, line 637); the random forest's
  constant (4.2, line 511); S3.19 note ᶜ (4.3, line 580); the S3.21 rows `Adopted arm`, E3a, E3m, E3, E6 and E10 (4.5,
  lines 674, 678-680, 684 and 688); the Link cell rule of 4.7 (line 806) and check 3.3 (lines 345-346: the source
  label keeps its own words); decision 18 (lines 1218-1219).
- V3-7: the header comment (2.9, line 309); section 5, what `tables_file` names (lines 1114-1116); and, outside this
  file, the two corrections of `OUT\spec\CHANGES_v2.md` (785 lines, not 786; the complete list of the number tokens
  that version 2 added), each marked "(corrected in version 3)".
- S10: this section, and its entry in the contents line (line 15).
- Left as in version 2 because the order does not name them: the short title of Table S3.18 in the table of section 4
  (line 391) and the heading of 4.2 (line 475) still say "the rivals left out" (neither is printed); the S3.28 caption
  (line 931) defines its pair's J ("more than 10⁻¹² of its total") without the region weighting that the S3.19
  caption now states; E8's "What it checks" (line 687) still says "kept predictions"; decision 6 (line 1182) already
  agrees with the new count clause (no count is printed without an interval); section 9 keeps the version-2 record
  and its line numbers. The version-2 helper scripts `s07_diff_v1_v2.py`, `s10_check_new_texts.py` and
  `s12_check_changes_file.py` read `TABLE_SPEC.md` as version 2; they now hold for `TABLE_SPEC_v2.md`.
- Helper scripts of version 3 in `OUT\spec\` (read-only, print only): `s13_diff_v2_v3.py`, `s14_check_new_texts.py`,
  `s15_source_checks_v3.py` (the order's claims against the sources it names), `s16_v2_number_tokens.py` (the line
  count and the number tokens of version 2, behind the CHANGES_v2.md corrections) and `s17_check_changes_v3.py`
  (every text quoted in CHANGES_v3.md against the file it is quoted from).
- Opened for version 3: the order, the brief, version 2 of this spec, `CHANGES_v2.md`, `tables_agreed.md` and
  `tables_agreed_v1.md` (and the SHA-256 of the builders' tables.md and the `tables_file` of
  `OUT\reconcile\cells.json`); `SHAP\PROTOCOL.md` lines 168-181 and 480-519; `ROOT\paper\draft\GLOSSARY.md` (its
  header and the rows that the order names, and the row "region"); `ROOT\paper\draft\03_protocol.md` (its headings
  and the baselines paragraph of Section 3.3); `ROOT\paper\draft\tables\table_3.md` lines 2-20;
  `SHAP\scripts\tr_rebuild.py` lines 690-754 and `ROOT\engine\treeroute\pipeline\stages.py` lines 165-201 (read, not
  run); `V\_lead\outputs\bardl_ties.txt`; the five rebuild `gates.json` (E10, E6, result);
  `OUT\skeptic\k08_share_bases.py` and `k09_number_tokens.py` (read, not run); the helper scripts of version 2
  (`s07`, `s08`, `s10`, `s12`).
