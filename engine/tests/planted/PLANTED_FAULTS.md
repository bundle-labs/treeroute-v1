# Planted faults for the check validators

Each row breaks exactly one rule of the clean planted package (`tests/planted/build.py`: 3 groups x 4 units,
monthly 2001-2010, one driver store, a feature script with one router-context column and one engineered lag).
The named guard must refuse the fault, or flag it where the guard's signed contract is report only.
`tests/test_check_planted.py` runs every row and checks that the clean package itself has no refusal; it also
checks that this table and `tests/planted/faults.py` list the same faults.

- **detection**: the guard finds the fault in the data or the code.
- **rule enforcement**: the guard enforces a DECLARATION. A wrong but complete fact (for example a window that is
  declared backward but is really centred) passes; what is refused is a missing, unsigned or inconsistent
  declaration.
- **Level**: `quick` runs `check`, `deep` runs `check --deep`, `validator` calls the validator directly, because
  the engine's own lookups cannot produce that fault inside a package (the predecessor lookup never reads across a
  gap; nothing in a package can type a lag).

| ID | Guard | Level | Expected | Kind | Planted fault |
|---|---|---|---|---|---|
| PF01 | G-CLOSED | quick | refuse | detection | a column in the data with no catalog row and no verdict |
| PF02 | G-CLOSED | quick | refuse | rule enforcement | keep_unreviewed on a column whose timing facts are unverified |
| PF03 | G-CLOSED | quick | refuse | detection | a catalog row and verdict for a column no store holds |
| PF04 | G-LAG | quick | refuse | rule enforcement | a lag fact that cannot be computed: an unknown window with no signed bound on a kept column (a wrong but complete window passes) |
| PF05 | G-LAG | validator | refuse | rule enforcement | a typed lag: the lag map differs from R8's recomputation |
| PF06 | G-EPOCH | deep | refuse | rule enforcement | a kept static column whose content epoch lies after the cut (a post-window snapshot), without a 'freeze' verdict |
| PF07 | G-EPOCH | deep | refuse | rule enforcement | a post-cut label: the target calibrated past the donor train end, not disclosed |
| PF08 | G-LINEAGE | quick | refuse | rule enforcement | a kept co-product (lineage assimilates the target) without a signed exception |
| PF09 | G-LINEAGE | quick | refuse | rule enforcement | a sum group with mixed verdicts |
| PF10 | G-LINEAGE (deep) | deep | flag | detection | a banned sum-group member rebuilt as the total minus a kept member (report only by contract) |
| PF11 | G-HIST | quick | refuse | rule enforcement | a feature output declared as reading the target (a lag of the own target) |
| PF12 | G-HIST (sample) | deep | refuse | detection | a store column that is the own target one step earlier, declared as an ordinary driver |
| PF13 | G-HIST (sample) | deep | refuse | detection | a feature script that reads the target at t (declared as a lag of a driver) |
| PF14 | G-KEYS | quick | refuse | rule enforcement | a column derived from a key (the calendar month) entering the trees |
| PF15 | G-SPLIT | quick | refuse | detection | split.yaml excludes a group the data do not hold |
| PF16 | G-SUPPORT (deep) | deep | refuse | detection | the presence-only refusal: only rows with a large label are stored |
| PF17 | G-SUPPORT (deep) | deep | refuse | detection | a cadence gap: one unit misses one month inside the record |
| PF18 | G-FACTS | quick | refuse | rule enforcement | an unsigned fact: 'assumed' timing facts with no reviewer on a kept column |
| PF19 | G-MISSING | deep | refuse | rule enforcement | a kept column vanishing in a test year (R30) with only a keep_unreviewed verdict |
| PF20 | G-MISSING (deep) | deep | flag | detection | a column all missing in one group-year inside files that exist (report only by contract) |
| PF21 | G-CADENCE | deep | refuse | detection | a fake-monthly column: declared monthly, constant within every unit-year |
| PF22 | G-CALENDAR | validator | refuse | detection | a row-shift lag across a missing step |
| PF23 | G-DERIVED (recompute) | deep | refuse | detection | the feature script computes lag 2 while declaring lag 1 |
| PF24 | G-DERIVED | quick | refuse | detection | a feature script that fits a model (.fit) |
| PF25 | G-SENTINEL (deep) | deep | flag | detection | an undeclared fill code (-9999) left in a driver (report only by contract) |
| PF26 | G-SENTINEL (deep) | deep | refuse | detection | a sentinel value left in the target (the read refuses it, D30) |
| PF27 | G-RANGE | deep | refuse | detection | an out-of-range share: a fraction above 1 in 1 of 12 months |
| PF28 | G-RANGE | deep | flag | detection | one value out of range, under 0.1% of the column: flagged with its count |
| PF29 | G-JOIN | deep | refuse | detection | a join that duplicates rows: a store file repeats unit x step keys |
| PF30 | G-JOIN | deep | refuse | detection | a store's column set differs from its catalog (a declared column missing from the files) |
| PF31 | G-MISSING (files) | deep | refuse | detection | a driver store holds no file for one group, which no store fact declares absent |
| PF32 | G-LINEAGE | quick | refuse | rule enforcement | the PF08 co-product with an exceptions.yaml entry whose owner reads 'UNSIGNED -- basis: ...' (a disclosure, not a signature) |
| PF33 | G-EPOCH | deep | refuse | detection | the target outlasts the drivers by 2 years and is calibrated through 2008: R3 on the joined rows puts the train end at 2006 |
| PF34 | G-MISSING (files) | deep | refuse | detection | one driver YEAR file is missing inside the store's record (one group, one test year), which no store fact declares absent |

Notes for the owner:

- Report-only guards (their signed contracts never block): G-SENTINEL's deep scan of undeclared codes, G-MISSING
  (deep) and the G-LINEAGE reconstruction test. Their rows expect `flag`. A sentinel in the TARGET is refused at
  read (D30), so PF26 refuses.
- PF04 is the lag-fact row: a WRONG but complete window cannot be detected (declarations are enforced, not
  detected); an uncomputable window is refused. PF05 covers a typed lag at the validator level.
- PF32: the schema only asks for a non-empty `owner`, and the real packages write `'UNSIGNED -- basis: ...'` in
  every exceptions.yaml entry ("the owner signs by replacing UNSIGNED"). Such an entry is a disclosure, not a
  signature, so the guards that accept a signed entry (G-LINEAGE, G-EPOCH's target rule, G-FACTS' test exposure)
  still refuse, and the message quotes the unsigned owner field.
- PF07 reads 'a post-cut label' as a target calibrated with information past the donor train end (G-EPOCH's
  target rule). Label reads after a cut at run time are G-LOCK / G-FITCUT, enforced by the vault and the fit
  context, not by `check`.
- PF06 plants a CONTENT epoch (plan 1.3: release and snapshot dates are never used by G-EPOCH; content time only).
  G-EPOCH compares content_epoch on every cadence kind (static included) and observed_through of a static or
  epoch column with EVERY R11 cut (each lead's fit and guard cut). observed_through of a regular column is an
  owner decision, flagged, never refused (see the guard's docstring).
- PF33: the deep check derives the windows with the engine's rules (R3 on the joined rows, R4, R5, R6, R7, R10,
  R11) on the deep pass's rows. The old estimate ('last label year minus 4') put the train end at 2008 and passed
  this target; R3 puts it at 2006 and G-EPOCH refuses.
- PF34: G-MISSING (files) checks (group, year) pairs (the target's years inside the store's record), not only one
  file per group; the rows of the missing year count as missing in the shares and as rows without a file in G-JOIN.
- PF22 is VALIDATOR level only: the deep G-CALENDAR builds its reads with the engine's own predecessor lookup on the
  grid's keys and checks those reads, so no package content can fail it. A package-level row-shift lag is caught by
  the G-DERIVED recompute (PF23 is that case), and a census hole by G-SUPPORT (PF17).
