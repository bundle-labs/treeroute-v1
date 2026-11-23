# AC_REPORT: ruling AC built, checked and written into the rival Part draft

Written 2026-10-21. Everything written is under `D:\treeroute\rivals_build`. The LIVE engine was only read (no file in
it changed). No rival test score was made or read; the only real-data runs were the smoke exports and the coral
tune-only dry pass.

## ATTENTION: one decision before you sign (patience)

Patience 50 still cuts the Tweedie rival short on coral. Ruling AC did not touch it, and it is pre-registered, so
only you can change it.
- One Tweedie setting (127 leaves, min child 200, power 1.2) stops at round 225, best at round 175 (inner MAE
  6.5676). Left to run, its best is round 320 (6.5330). That would beat the locked Tweedie pick (6.5664).
- So on coral Tweedie is about **0.033 MAE weaker** than its own grid allows. LightGBM is not affected on the two
  settings measured.
- Options:
  - **(a) keep 50.** Nothing more to do. The draft already discloses the cut with these numbers (section 9 item 14).
  - **(b) raise it to about 150.** One constant (`rivals\models.py:78`). Cost on coral: seconds. On the four grid
    problems: about +0.6-1.6 h (x) of tuning. Then the code hash changes, so the tests and the coral dry pass run
    again, the coral check value changes, and the draft gets the new hash.
- My suggestion: (b), since a rival tuned below its own grid is easy for a reviewer to attack and it costs little.
  Your call.

**Ready to sign: no, not yet.** It is waiting only on the patience answer. If you answer "keep 50", the draft is
ready to sign as written, with no further change.

## What was done

- **Code: no change needed.** The AC check found no bug; the only open point is the patience above. The harness
  hash stays **`bc62c8056bcabb83ca3f4abb704499685658b3a0ba8738e31231883cbdbc9057`** (re-checked after every run).
- **The fire smoke export test, skipped by the check for RAM, now ran and passed** (5.5 GiB free; 116 s; P1-P14 pass
  at leads 0, 6, 12; `pt\ac\fire1.log`). So every real-data test has now passed on this code.
- **PREREGISTRATION_DRAFT_rivals_common.md** (still DRAFT, UNSIGNED; old copy in `_moved\20261021_preAC4_docs`):
  - new file hashes and harness hash (section 1) and in the signature block (section 11);
  - AC1: 255 bins in tuning and in every final fit (section 2, section 3 items 7, 13, 21); the 63-bin weakness
    disclosure is removed and replaced by a short "255 bins everywhere" note (section 9 item 16);
  - AC2: the extension only for a LightGBM or Tweedie trial that ran to the 800 cap without a patience stop
    (section 3 item 9; section 9 items 12, 18);
  - AC3: the out-of-core Random Forest kept as built (section 9 item 2; section 10b);
  - the lead-0 guard is now the tuning trial for every rival, so picks.json's numbers are the reported ones
    (section 3 item 13);
  - the new coral dry picks (section 7), the patience cut measured at 255 bins (section 9 item 14), a new section
    10b for ruling AC, and a dated change note. No open markers.
- **RIVALS_OWNER_COMMANDS.md** (old copy in the same folder): the new coral check value, the removed lead-0 guard
  fit note, the 63-bin wording, and the times (below).

## Final coral dry picks (inner window only; picks content `14b18f11...`)

| Rival | Pick | Inner MAE |
|---|---|---|
| Ridge | log_c, alpha 1 | 6.350 |
| RF | arcsine, max_features 0.5, min leaf 50 | 6.690 |
| LightGBM | arcsine, 127 leaves, min child 200, round 41 | **6.385** (was 6.546 under AA, 6.439 before AA) |
| Tweedie | power 1.5, 31 leaves, min child 200, round 146 | 6.566 (AA's 6.452 was a 63-bin number, not the reported model) |
| hgb_l1 | arcsine, 127 leaf nodes, min leaf 20, 400 iterations | 6.355 |

All pass our safety net against the donor median (9.742). No flag. No LightGBM or Tweedie trial was extended.
Your coral check value: `14b18f1138ad3beac55db2cfa77a6a259b0c589208fa45eba287b7a040e7ca0f`.

## Total time for the common board

**About 33-62 h of machine time over about 7-12 overnight sessions (x), the same as after AA.** Worst case, if
every LightGBM trial runs to 800 and is extended: about +33 h (was +28 h).
- 255 bins make each tuning round about 14% slower, but AC removes AA's extra lead-0 guard fit, so the two about
  cancel: LightGBM + Tweedie fitting is about 12.1 h in the middle case (AA: 12.6 h).
- The Random Forest is unchanged at about 16-23 h.
- Coral itself: tune about 4 min (measured 227-230 s), all of coral about 15 min.
- The fire probe gives the first real figure; I re-price after it.

## Files

- `D:\treeroute\rivals_build\PREREGISTRATION_DRAFT_rivals_common.md`
- `D:\treeroute\rivals_build\RIVALS_OWNER_COMMANDS.md`
- `D:\treeroute\rivals_build\AC_CHECK_REPORT.md` (the check), `pt\ac\fire1.log` (the fire smoke run)
- Old copies: `D:\treeroute\rivals_build\_moved\20261021_preAC4_docs\`
