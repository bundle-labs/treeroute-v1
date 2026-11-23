# AA_REPORT: the AA review fixes, for the owner

Written 2026-10-21. Everything written is under `D:\treeroute\rivals_build`. The old code and docs were copied to
`_moved\20261021_preAAfix_code\` first, and nothing was deleted. LIVE was only read. No rival test score was made or
read. The only real-data runs were the smoke-size exports and the coral TUNE-ONLY dry pass.

## ATTENTION (one choice for you before you sign)

**1. The 63-bin speed-up CAN weaken the LightGBM and Tweedie rivals.** Ruling AA3's words "the reported rival is not
weakened" do not hold, and I have withdrawn them.
- **Why:** the setting and the round count are picked at 63 bins, then the final model is fitted at 255 bins at
  that same round count (`harness.py:2141`, `:2162`). A good round count at 63 bins can be a poor one at 255.
- **On coral (inner rows only):** the 255-bin model at the pinned round 63 scores about 6.47. Its own best 255-bin
  round would score 6.385, and the pre-AA pick scored 6.439.
- **Today:** the code follows AA3 as you ruled it, and the Part discloses the weakening (section 9 item 16).
- **Your options:**
  - (keep) sign as it is, with the disclosure;
  - (d) tune at 255 bins: the weakening is gone. Cost: about 5-10% of the LightGBM tuning time, under 1 h in
    all. The bins save little anyway (AA_CHECK_REPORT.md section 4).
  - (e) keep 63 bins for choosing the setting, then run the picked setting once at 255 bins with the same early
    stopping, and pin that run's best round. On the toy it closed about 91% of the gap, with no extra fit overall.
- **My recommendation: (d).** It is the simplest, it removes the problem fully, and it costs little.
- (d) or (e) changes the code hash and the coral picks, so I would rebuild and update the draft before you sign.

**2. (smaller) A patience-stopped trial is still "extended" and only repeats itself.** AA2 says the extension
applies, so I left it in. Extending only the trials that reach the 800 cap would save time and change no pick. That
change needs your word.

## What changed (harness code hash e5032ad5 -> c52babae)

- **Code:**
  - `harness.py` `pick_flags`: LightGBM and Tweedie are flagged only for a pick at round 1 (`edge_round_1`).
    Before, the round-63 pick was wrongly called an edge. hgb_l1 keeps `edge_rounds_100`.
  - `harness.py` lock: picks.json now says that its LightGBM and Tweedie numbers belong to the 63-bin tuning
    model (`inner_mae_and_n2_are_of`). The rival's own numbers come from `done_<learner>.json` `guard`.
  - `harness.py` board.json rules: the bins rule and the early-stop rule are reworded.
  - `export.py`: the text now says "P15 only with --p15 or on an accepted run". It also no longer says that I5-I7
    check a copied R30 share (that claim was circular).
- **Tests:** they follow the new flag. The AA4 timing test now also keeps a time-stamped evidence file.
- **Docs:**
  - SPEC_RIVALS.md: 2.10, 3.4a, 3.5, 3.6 and a new 7a.
  - AA_CHECK_REPORT.md section 3 has corrections:
    - NDVI's skipped count is about 7-23 h;
    - the separability saving is up to 1.58 h;
    - the R30 saving is not yet measured on a real export.
- **Pre-registration (DRAFT, UNSIGNED):** it now covers AA1-AA4 in the protocol (items 20-22) and in the
  disclosures (items 4 and 14-18):
  - patience 50 and the any-round tilt;
  - 63/255 bins and the weakening;
  - the repeated extension;
  - the lean export, its two skipped steps, the pm25 R30 limit and `--full-engine-checks`;
  - the dropped board, naming ruling D, L3 and Q44, with the plan lines it supersedes.

  It also has the new file SHAs, hash c52babae in the signature block and a dated change note. It has no open
  markers.
- **Owner commands:**
  - new times;
  - the one new flag, with "don't use it; never on NDVI";
  - an optional pm25 audit;
  - a check of fire's `derive` time;
  - the new coral check value;
  - the "no phase 2" line;
  - a close-apps and free-RAM check before each session.

## Tests (on c52babae)

| run | result | log |
|---|---|---|
| full suite, real-data tests on (`RIVALS_REAL=1`) | **166 passed, 1 skipped** (the opt-in heavy RF test), 25 min | `pt\aafix\full1.log` |
| AA review folder | **26 passed, 1 xfailed.** The xfail is the reviewer's record of the AA3 weakening, still true by design. | `pt\aafix\review_aa1.log` |
| AA4 defo smoke, lean vs full | files byte-identical; P1-P15 pass; full 49.7 / 50.4 s, lean 44.5 / 44.8 s | `evidence\aa4\defo_smoke_timing_20261021T060822Z.json` |

## Coral dry picks (inner window only)

| learner | pre-AA (fb8656a9) | AA (e5032ad5) | now (c52babae) |
|---|---|---|---|
| ridge | log_c, alpha 1, 6.350 | same | same |
| rf | arcsine, mf 0.5, leaf 50, 6.690 | same | same |
| hgb_l1 | arcsine, 127 / 20, 400 it., 6.355 | same | same |
| lgbm | arcsine, 31 / 200, 200 rounds, 6.439 | arcsine, 127 / 200, round 63, 6.546*, flag edge_rounds_100 | same pick, **no flag** |
| lgbm_tweedie | log, 127 / 200, p 1.2, 400 rounds, 6.565 | log, 31 / 20, p 1.5, round 181, 6.452* | same |
| picks content | 3b5a33f1 | 2a3e224e | **2a3e224e** (trials.csv and all 53 inner prediction files byte-equal) |

\* These are 63-bin tuning-model numbers. All picks are N2-eligible against the donor median (9.742). Coral tuning
took 222.8 s.

## New total time for the common board

- **About 33-62 h of machine time, over about 7-12 overnight sessions** (it was 40-70 h, over 8-14).
- Worst case, if every trial extends: up to +28 h more.
- The LightGBM part assumes trials stop near round 350. The fire probe gives the first real figure, and I re-price
  after it.

## Ready to sign?

**Yes, as built.** `PREREGISTRATION_DRAFT_rivals_common.md` is complete for code c52babae, with the weakening
disclosed. If you choose (d) or (e) in ATTENTION 1, or the extension change in ATTENTION 2, tell me first. I would
rebuild, re-run the tests and the coral dry pass, and update the draft with the new hash before you sign.
