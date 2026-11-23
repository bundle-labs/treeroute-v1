# AUDIT_CHECKLIST -- coral_draft (table package)

The human checks no code can do (APP_PLAN.md 1.2; SPEC_TABLE_MODE.md 1.4, 1.7). **UNSIGNED.** Drafted by the agent
on 2026-10-19. Every box is open until the owner ticks it and signs at the bottom. Evidence pointers say where to
look; they are not conclusions. Counts: D:/treeroute/coral_build/coral_data/visits_census.json.

## A. Package checks

| # | Check | Where to look | Done |
|---|---|---|---|
| 1 | Target lineage | GCBD SQLite 11_24_21 (D:/coral/target/raw/gcbd). Recipe coral_smoke_regress.py:56-77: Reef Check Population rows, mean of S1-S4; AGRRA, FRRP, McClanahan, Donner Percent_Bleached; Kumagai and Safaie excluded (ordinal only). 20,244 labelled samples. The flat CSV is fabricated and not read (D:/coral/target/README.md). | [ ] |
| 2 | Fill codes and caps | No fill code is written: missing = NaN. Caps, not fills: days_since_dhw4 3650 (legacy 99999), cyc_days_since_close 3650, cyc_mindist_* 9999 km, mhw_since_end 365. -9999 in dmi.txt read as missing (coral_extra_drivers.py:63-66). | [ ] |
| 3 | Label grain and dating | One row per visit = (site, date); repeat Sample_IDs averaged (3,080 merged visits, 1,282 disagree). Date from GCBD Date_* (events_dated.date clamps day 28). Donner/Safaie day 15 = month precision: T = month end, features before the month start (2,128 visits, all train). | [ ] |
| 4 | Product vintages | GCBD 11_24_21; CoralTemp compact manifest = sst_full (5,139 files); IBTrACS v04r01 (to 2026-08-20); nina34.txt ERSST V6 (to Jul 2026); dmi.txt HadISST1.1 (to May 2026). Hash each input in the build manifest. | [ ] |
| 5 | Split design | Leave one ecoregion out. Test window 2016-2019 (owner ruling V3): visits after 2019 are not written (38); 2017-2020 is the declared sensitivity row. 11 groups excluded in split.yaml: the engine defaults refuse them (V5; O13/O14). 83 groups remain; 46 of them have no test row in the lead files and are donor-only (V6 b DRAFT option: they train trees and lend rows; nothing is scored for them), so scores cover 37 groups. The V6 (b) copy of `coral_tables/make_split.py --check` recomputes the list. | [ ] |
| 6 | Unit definition | Package unit = GCBD ecoregion id + coral_safe.site_key(lat, lon) at 4 decimals (about 11 m). No site key falls in two ecoregions (measured). Group = ecoregion NAME. | [ ] |
| 7 | Unit set not chosen from labels after the train end | Units are every labelled visit's site with an SST series and enough history; nothing reads a label to pick them. | [ ] |
| 8 | Legal range cites the protocol | [0, 100], percentages by protocol; out-of-range rows dropped by the recipe (0 today). | [ ] |
| 9 | Bathymetry | GEBCO / SRTM15+ not used: optical inversion of the reef after the survey (CORAL_STATE.md:111-114). | [ ] |
| 10 | Columns not written | The 77 frame's mask_* (data-product mask), GHS-POP shape columns (content dated 2018-2022: GHSL_Data_Package_2023.pdf pp. 46-47; N2), absolute nino34 and every lag-0 index column. Listed in ban.yaml's header. | [ ] |

## B. Ruling U2: the owner vouches for the feature timing

The engine cannot recompute hand-built features (ruling U2, OWNER_RULINGS_2026-10-06.md:91). By signing below the
owner states, for every row of every lead file (SPEC_TABLE_MODE.md 1.7):

1. Every feature and context value of a lead-L row uses only data dated strictly before its issue date
   (target date minus L). The builder uses the stricter cut C = anchor - L (anchor = the target date, or the month's
   first day for a month-precision visit); SST and cyclone windows end before C - g (g = 1 day by default, UTC days).
2. No feature reads the row's own label, a label of any test row, or any label dated on or after the issue date.
   No column of these files is computed from any label.
3. The issue date column equals target date minus L (the engine checks it).
4. The same row id means the same visit, with the same label, in every file (the engine checks it).
5. The target date is the label's last content day.
6. feature_end is the last content day any feature window of the row may read at that lead (a window bound), and it
   is before the issue date (the engine checks the second part: T-FEATEND).

Evidence the builder leaves for this statement (SPEC_CORAL_TABLES.md 3.4): the per-family "latest source day minus
issue day" (always below 0) in build_manifest.json; the look-ahead canary (rows rebuilt from sources truncated at the
cut, compared byte for byte); the replay check against forecast_features_L0.parquet and _L365.parquet on untouched
rows; and coral_tables/check_tables.py, an independent checker that re-reads the lead files, recomputes the MMM, the
SST heat, cyclone, nino34a and season columns from data cut at C - g / C, and has a negative control (a cut one day
later must fail). Tiny build 2026-10-19: all passed (coral_data/tiny/build_manifest.json, check_report.json).

Open timing facts the owner must accept or change before signing:
- CoralTemp content reach after its day stamp is unverified (a gap of g = 1 day covers the UTC day stamp only;
  option --sst-gap-days, P17).
- ERSST V6 reach +2 months is assumed from ruling R-A (written for ERSSTv5).
- DMI window bound {3, month, centred} is proposed (dmi_lag* stay conditional until signed).
- IBTrACS best tracks are post-season products (disclosed).

---

Signed: ____________________   Date: ____________

(The loader checks only that this file exists; its content and signature are checked by a later validator.)
