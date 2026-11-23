# Coral label audit — the go/no-go question, answered

Run against `D:\coral\target\raw\gcbd\Global_Coral_Bleaching_Database_SQLite_11_24_21.db`
(figshare article 17076290, file 31573496, 23.5 MB, CC0, version 1, modified 2022-01-14).
Every number below is **counted from that file**, not quoted from a paper. Joined row count is
34,846 — which identifies the SQLite as the source of the "34,846" figure, one of the three totals
in print.

---

## The headline: there is no single target column

Seven sources contribute to this database and **five different columns carry the bleaching signal.**
Not one column is populated by more than one source group. Counts are non-NULL:

| source | rows | `Percent_Bleached` | `Severity_Code` | `Bleaching_Prevalence_Score` | `S1`–`S4` segments | other |
|---|---:|---:|---:|---:|---:|---|
| Reef_Check | 22,325 | **0** | **0** | 0 | 22,308 / 22,293 / 22,150 / 22,032 | — |
| Donner | 6,301 | 3,489 | **6,301** | 0 | 0 | — |
| AGRRA | 2,852 | **2,852** | 0 | 0 | 0 | — |
| FRRP | 2,394 | **2,394** | 0 | 0 | 0 | — |
| Kumagai | 667 | 0 | **667** | 0 | 0 | — |
| McClanahan | 226 | **226** | 0 | 0 | 0 | `Number_Bleached_Colonies` 226, `bleach_intensity` 226 |
| Safaie | 81 | 0 | 0 | **81** | 0 | — |

`Percent_Bleaching_Old_Method` is non-NULL in **zero** rows across the whole database — a dead column.

**This alone explains most of the confusion in the literature.** Any analysis that reads
`Percent_Bleached` gets AGRRA + FRRP + McClanahan + part of Donner — 8,961 rows — and silently drops
Reef Check entirely, which is 64% of the database. Any analysis that pools the columns has to invent
a mapping between five incompatible encodings, and different papers invented different ones.

---

## Finding 1 — the Reef Check zeros are REAL. The "coerced blanks" theory is refuted.

This was the single highest-risk unknown in the whole project, and it is now settled.

Reef Check's signal lives in four transect-segment columns, `S1`–`S4`. They are:

- **non-NULL in ~22,300 of 22,325 rows** (only 17–293 missing per column)
- **continuous on 0–100**, with **126–139 distinct values each**
- zero in ~16,900 rows per segment, and **strictly positive in ~5,000–5,500 rows per segment**

A field that was blank-coerced-to-zero does not come with five thousand positive values spread over
130+ distinct levels beside it. **These are measured zeros: four independent belt-transect segments
each recording 0% bleached.**

**Consequence: the negative class is real, and the ~28,000 rows one published analysis excluded were
excluded on a false premise.** That is worth stating in the paper, because the field's flagship
global regression and its most-cited skeptical reanalysis disagree about exactly these rows.

---

## Finding 2 — but Reef Check is double-stored, and the two copies are different quantities

Here is the mechanism that a coin-flip AUC would fall out of.

| | |
|---|---|
| Reef Check rows | 22,325 |
| distinct survey events (`Sample_ID`) | 11,309 |
| events carrying **both** a Population and a Colony row | **11,016 (97.4%)** |
| events carrying only one level | 293 |

Reef Check is the **only** source with a `Bleaching_Level` distinction — every other source is NULL
on it. So essentially every Reef Check survey appears **twice**: once as `Population` and once as
`Colony`. That is the 1.94× inflation seen in the Red Sea counts and a large part of the ~53% CSV
overcount.

And the two copies are not duplicates. On the **same 11,016 surveys**:

| | Population (prevalence) | Colony (severity) |
|---|---:|---:|
| mean segment value | **2.53%** | **7.22%** |
| median | 0.00% | 0.00% |
| Pearson r | **0.5689** | |
| disagree on zero vs non-zero | **650 surveys (5.9%)** | |

Population is *how many colonies are bleached*. Colony is *how much of a colony's surface is
bleached*. They differ by **2.85× in level** and correlate at only 0.57 — an independent confirmation
of the r = 0.445 measured on a different paired sample.

> **A pooled read of `S1`–`S4` without splitting on `Bleaching_Level` averages prevalence together
> with severity, on 97.4% of the rows, in the source that is 64% of the database.** That is a
> concrete, testable mechanism for the AUC ≈ 0.50 result — and it is a defect in the *analysis*, not
> in the labels.

**This is the first thing to test, and it costs an afternoon:** re-run the DHW-only logistic three
ways — Population rows only, Colony rows only, pooled — against a clean self-computed DHW. If the
split versions lift off 0.50 and the pooled one does not, the mystery is solved and ~28,000 rows come
back.

---

## Finding 3 — Donner contributes no negatives at all

Of Donner's 6,301 rows: `Severity_Code` is non-NULL on all of them, with **5,771 positive, 530 coded
−1 ("% unknown"), and zero coded 0 ("No Bleaching")**. `Percent_Bleached` has 3,489 positive values
and, again, **not one zero**.

Donner inside GCBD is a bleaching-**event** compilation — records exist because something bleached.
Used alone it cannot train a classifier, and pooled it shifts the base rate. (Note this is the Donner
subset *inside GCBD*; the separate Urcelay–Donner Zenodo database does carry real zeros and is a
different object.)

---

## The negative class, assembled honestly

| source | negative rows | negative **events** |
|---|---:|---:|
| Reef_Check (all four segments 0) | 14,716 | **7,111** |
| AGRRA (`Percent_Bleached` = 0) | 1,194 | 1,194 |
| Kumagai (`Severity_Code` = 0) | 332 | 332 |
| FRRP (`Percent_Bleached` = 0) | 201 | 201 |
| Safaie (`Bleaching_Prevalence_Score` = 0) | 21 | 21 |
| McClanahan | 2 | 2 |
| **non-Reef-Check total** | **1,750** | **1,750** |

Reef Check is **89.4% of negatives at row grain** — matching the independent 89.4% from the region
survey — and **80.2% at event grain**. Either way the negative class is one volunteer programme, and
if it were ever excluded the remaining 1,750 negatives would not support a global model.

**So the project's viability rests on Finding 1, and Finding 1 says the zeros are sound.**

---

## Two more ordinal cut sets confirmed in the file

The database ships **two mutually incompatible ordinal scales**, which is why harmonisation is lossy:

| `Severity_Code` | | `Bleaching_Prevalence_Score` | |
|---|---|---|---|
| −1 | % unknown | 0 | No bleaching |
| 0 | No bleaching | 1 | ≤ 10% reef area |
| 1 | Mild, 1–10% | 2 | 10–25% reef area |
| 2 | Moderate, 11–50% | 3 | 25–50% reef area |
| 3 | Severe, > 50% | 4 | > 50% reef area |

The boundaries at **10 / 50** and **10 / 25 / 50** do not nest, and the second measures *reef area*
while the first measures *colonies*. The 4-class Donner cut set `{<1, 1–10, >10–50, >50}` folds
`Severity_Code` cleanly and `Bleaching_Prevalence_Score` **only by collapsing its 2 and 3**.

Also note `Severity_Code = −1` is a **sentinel, not a level** — 530 Donner rows. Sorted naively it
lands below "No bleaching". This is the same failure family as the AIMS scale where `-1` means 1–5%,
and as the int32 `−2147483648` that poisoned 47 NDVI regions.

---

## What to do next, in order

1. **Split on `Bleaching_Level` before anything else.** Never aggregate Reef Check without it.
2. **Work at event grain, not row grain.** 11,309 events, not 22,325 rows. Every count in the
   literature that uses rows is inflated ~1.94× for Reef Check.
3. **Run the three-way DHW test** (Population / Colony / pooled) against a self-computed leak-free
   DHW. This is the go/no-go and it is now a two-day job with a clear hypothesis.
4. **Carry `label_provenance` on every row** — which source, which column, which encoding. It cannot
   be reconstructed later, and five encodings make it mandatory.
5. **Treat `Severity_Code = −1` as missing**, explicitly, before any sort or cast.

---

## Finding 4 — the segment scale is settled: AVERAGE the segments, never sum them

`Subquery_6_Calculated_Reef_Check_Segments` carries both the raw and the derived value, so the
protocol is recoverable from the file:

- **`Calculated_Sn = Sn × 2.5` for every one of its 28,717 rows** — the ratio is exactly 2.5, with no
  exceptions.
- Raw `Sn` maxes at **exactly 40.0**. Reef Check point-samples a 20 m segment at 0.5 m intervals =
  **40 points**, so the raw value is a point *count* and `count/40 × 100 = count × 2.5` is the percent.
- The table spans three substrates: **Hard Coral 14,359**, Nutrient Indicator Algae 11,979, Fleshy
  Seaweed 2,379. Only the Hard Coral subset is relevant here — it is a cover table, not a bleaching table.

And the practical consequence for `Bleaching_tbl`:

> **`Bleaching_tbl.S1`–`S4` are ALREADY percentages, not counts.** Max is 100.0 and **90.5% of values
> are exact multiples of 2.5**. So the four segments must be **averaged** to get a survey-level
> percent. Summing them inflates by 4× — and would push a genuine 30% survey to 120%.

The 9.5% that are *not* multiples of 2.5 are unexplained and worth a look; the most likely cause is
surveys run at a different point count.

## Finding 5 — the flat CSV is not the same database, and it manufactures its target column

This one matters beyond this project, because much of the published work used the CSV.

| source | SQLite | flat CSV | delta |
|---|---:|---:|---:|
| Reef_Check | 22,325 | 28,821 | **+6,496** |
| Donner | 6,301 | 6,307 | +6 |
| AGRRA | 2,852 | 2,848 | **−4** |
| McClanahan | 226 | 234 | +8 |
| **Nuryana** | **0** | **5** | **+5** |
| **Setiawan** | **0** | **4** | **+4** |
| FRRP / Kumagai / Safaie | 2,394 / 667 / 81 | same | 0 |
| **TOTAL** | **34,846** | **41,361** | **+6,515** |

Two sources exist **only** in the CSV. AGRRA is *smaller* in the CSV. These are not two exports of
one thing — **they are different databases sharing a name**, which is the real reason three different
totals are in print.

And the CSV has no segment columns, no `Severity_Code`, no `Bleaching_Prevalence_Score`. It has one
column, `Percent_Bleaching`, into which five incompatible encodings were collapsed — by substituting
**class midpoints for ordinal codes**:

| source | its top four values in `Percent_Bleaching` | share of that source's rows |
|---|---|---:|
| Donner | **5.5, 75.0, 30.5, 100.0** | **42.9%** |
| **Kumagai** | **0, 30.5, 5.5, 75.0** | **100.0%** |
| Safaie | 5.0, 0, 75.0, 17.5 | 92.2% |
| Reef_Check | 0, 0.25, 0.5, 1.0 | 75.8% |

Read the `Severity_Code` lookup against those numbers and the fabrication is explicit: *Mild
(1–10%)* → **5.5**, *Moderate (11–50%)* → **30.5**, *Severe (>50%)* → **75.0**. Kumagai has only an
ordinal code in the SQLite, so **100% of its percentages in the CSV are invented.** Across the whole
file, four values carry **56.8%** of all non-null mass.

**`ClimSST == 262.15 K` in exactly 7,188 rows (17.4%)** — verified, and it is the column *minimum*
(range 262.15–307.22 K). 262.15 K is −11 °C: a sentinel wearing a plausible unit, positioned exactly
where a sanity check looking for absurd *highs* will not find it.

**Rule: model on the SQLite. Keep the CSV only as the artefact that explains other people's numbers.**

---

## Finding 6 — NCRMP's `NA` means "not applicable", not "not assessed". The MNAR fear is unfounded.

This was the second-highest-value unknown in the project. It is now settled, from
`D:\coral\target\raw\ncrmp\` (12 datasets, **631,621 colony rows**).

First, the coding scheme is not what a default CSV read shows. **`NA` is a literal coded value, not
missingness** — pandas' default `na_values` silently converts it, which is how it gets mistaken for
an empty cell. Read raw, `BLEACH_CONDITION` has five levels:

| code | meaning | Florida | USVI | Puerto Rico | Flower Gardens |
|---|---|---:|---:|---:|---:|
| `N` | no bleaching *(the negative class)* | 29.6% | 40.7% | 36.7% | **76.1%** |
| `P` | pale | 4.9% | 2.1% | 1.3% | 1.4% |
| `PB` | partly bleached | 1.9% | 0.8% | 0.8% | 0.8% |
| `T` | total | 0.4% | 0.1% | 0.6% | 0.0% |
| **`NA`** | **?** | **63.1%** | **56.3%** | **60.2%** | **21.7%** |

Florida 2024 reproduces the reported figure **exactly: 26,638 `NA` of 38,779 rows (68.7%)**.

Three independent tests, all pointing the same way:

**Test 1 — species.** Across 32 species with n ≥ 1,500, the `NA` rate runs **4.5% → 99.1%**:

| lowest | | highest | |
|---|---:|---|---:|
| *Siderastrea siderea* | 4.5% | *Favia fragum* | 99.1% |
| *Porites astreoides* | 8.1% | *Mycetophyllia ferox* | 98.7% |
| *Stephanocoenia intersepta* | 13.5% | *Mussa angulosa* | 98.6% |

A twenty-fold spread that tracks the split between abundant massive/encrusting corals and small,
cryptic ones. Effort does not vary by species.

**Test 2 — year.** 55.6%–75.7% across 2016–2024, no trend and no protocol step.

**Test 3 — the decisive one.** Of 1,794 surveys with ≥ 5 colonies:

| | |
|---|---:|
| **mixed** `NA` and non-`NA` within one survey | **1,726 (96.2%)** |
| all colonies `NA` | 68 (3.8%) |
| **no colonies `NA`** | **0 (0.0%)** |

If a diver had skipped bleaching assessment, the *whole survey* would go dark. Instead **not one
survey is free of `NA`, and 96% contain both** — the code is assigned per colony, by taxon.

> **Verdict: `NA` is structural exclusion by taxon or size class, not unrecorded data. NCRMP is
> usable, and its negative class (`N`) is sound.** The usable Florida-2024 sample is the 12,141
> non-`NA` colonies — matching an independent count of 12,138 to within 3.

**Bonus: NCRMP resolves the pale question explicitly.** `P` (pale) is a separate code from `PB`
(partly bleached) and `T` (total). Whether `P` belongs in the positive class is now a *choice* rather
than a guess — and it is a consequential one, since pale is 3–5× more common than partly bleached.

## Finding 7 — the Pacific hole is real, and now precisely dated

NCRMP publishes **12** datasets, not the 4 Atlantic ones usually cited. The Pacific arm exists — and
stops before the 2023–25 event:

| jurisdiction | rows | span | bleaching field |
|---|---:|---|---|
| USVI | 175,505 | 2013–**2023** | populated |
| Florida | 122,268 | 2016–**2024** | populated |
| CNMI / Guam | 72,834 | 2014–2022 | **0 non-null — column entirely empty** |
| Hawaii | 62,634 | 2013–2019 | populated |
| Puerto Rico | 55,388 | 2014–**2023** | populated |
| American Samoa | 47,678 | 2015–2018 | populated |
| PRIAs | 37,441 | 2014–2018 | populated |
| Flower Gardens | 14,178 | 2013–**2024** | populated |
| *(4 juvenile datasets)* | 43,695 | 2013–2022 | none |

**Every Pacific jurisdiction ends 2018–2022, and the one that reaches 2022 has an empty bleaching
column.** The independent claim that "72,834 rows have the condition field empty on all" is confirmed
exactly. So the recent-event hole in the Pacific is real, and it is not fixable from NCRMP.

---

## Still unverified

1. Does the Access rendering (`.accdb`, 46.5 MB, on disk) agree with the SQLite row-for-row? If it
   matches, the CSV is the odd one out and the SQLite is authoritative; if it matches the *CSV*, then
   the SQLite is a filtered subset and that changes which one to model on. **~1 hour, decisive.**
2. What are the 9.5% of `Bleaching_tbl.S1` values that are not multiples of 2.5? Likely a different
   point count; confirm against the Reef Check protocol.
3. Which of the two renderings did each published paper actually use? The +6,515-row gap plausibly
   explains the disagreement between the field's flagship regression and its main reanalysis, and
   that is a citable methodological result if it holds.
4. `Subquery_6` has 14,359 Hard Coral rows against 11,309 Reef Check survey events in
   `Bleaching_tbl`. Where do the extra 3,050 come from?
