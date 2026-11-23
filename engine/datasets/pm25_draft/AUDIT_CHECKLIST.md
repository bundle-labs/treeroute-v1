# AUDIT_CHECKLIST -- PM2.5 package

The human checks that no code can do (APP_PLAN.md 1.2, 'AUDIT_CHECKLIST.md'). **UNSIGNED.** Drafted by the agent on
2026-09-28 from the repo and the plan; every box is open until the owner ticks it and signs at the bottom. Evidence
pointers are where to look, not conclusions.

| # | Check (plan 1.2) | Where to look | Done |
|---|---|---|---|
| 1 | Target lineage and co-products | ACAG V5.GL.06 HybridPM25 (GWR with ground monitors). GWR covariates are flagged 'watch' on the sheet (V25_elevation_m, V26_slope_deg, V28_CTI, hand_m, dist_to_coast_km; pm25_ban.py:157-158). MERRA-2 is circular with ACAG (Q46). | [ ] |
| 2 | Fill codes | ACAG fill 9.96921e36 -> NaN in the ingest (plan 3.2; acag_pm25_ingest.py). Panel fills -32768, -32767, -2^31, -2^31+1 (store catalog; the -2^31 poison in 47/133 regions). | [ ] |
| 3 | Compositing-window dating | One ACAG file per calendar month (index_facts.yaml). Unknown: whether the monthly GWR calibration pools monitors across months (index audit owner item 7). | [ ] |
| 4 | Product vintages | ACAG V5.GL.06; panel monthly_panel_v170; GFED500m; EDGAR v8.1. | [ ] |
| 5 | Split design | pm25_split.py v3 (Part 554): emission-stratified, longitude stride, fire balance at the panel's share; v2 retired because its fire swaps used 2020-23 screen gains (Part 542). | [ ] |
| 6 | The unit definition (as delivered) | 4 km panel cells; ACAG pixels averaged inside each cell (acag_pm25_ingest.py). Unit id {group}_{ix}_{iy}. | [ ] |
| 7 | The unit set was not chosen from target values after the donor train end | Units are picked by stride over sorted ids (R18), 100 per group; M1 checks the stride reproduces the shipped cells. | [ ] |
| 8 | The unit set is declared, and whether it holds an all-zero unit (G-SUPPORT: a unit set with no all-zero unit is flagged) | 127 groups; target is a complete census (0.4% NaN in donor rows per the sheet). | [ ] |
| 9 | The target legal range cites the product's documented valid range (plan 1.3) | ATTENTION: no ACAG-documented valid range is cited; catalog.yaml leaves legal_range_source empty. | [ ] |

## Items the agent found while writing this package (for the owner)

- The target store D:/pm25_acag has no shared store catalog, so the target's dtype, units, cadence and fill code are declared nowhere yet.
- The static table (unit id, group id, lat, lon) does not exist yet; dataset.yaml points at the plan's default path for new data.
- ban.yaml (updated 2026-10-05) holds the full ban list installed under owner ruling J (OWNER_RULINGS_2026-10-05.md): 184 verdicts, keep 102, watch 19, conditional 22, ban 41; 119 tree features plus ctx:month and ctx:lat for the router. Its header lists what each J item changed.
- Open owner decisions from the J install (2026-10-05; details in ban.yaml and exceptions.yaml):
  - phenology_sos_doy: kept (watch) at the assumed one-extra-year bound (J2 b), which lags it 2 years and alone moves Y0 from 2003 to 2004 (R4, J5). Options: keep (Y0 2004; fire, which also keeps it, moves too), conditional (Y0 2003, ruling F3's value) or ban. expected_derived.json marks Y0, inner fit and h provisional until then.
  - aglw_* (6): the 2022-23 layers are the 2021 layer times India's FAOSTAT ratios, written for every region; the nowcast's 2023 test rows and lead 6's July-December 2023 targets read the 2022 layer. Options: rebuild with each country's ratio, carry 2021 forward, or keep and disclose (disclosed now).
  - burn_lag1: with burn_frac at lag 1 (J1) it holds the same month t-1 value. Options: keep the duplicate, move it to t-2, or drop it.
  - co_measured_with_target is unanswered on the kept time-varying columns; G-FACTS will block once built.
  - Timing facts to SIGN (all 'assumed', none signed): nitrogen_gkg units and range, V30 legal minimum (J4); deeprec_twsa reach 3 months, phenology_sos_doy window (J2 b); GFED burn_frac reach 1 month (J1). Windows still UNWRITTEN, so R8 refuses (G-LAG) until signed: noi (J1: {3, month, centred}), epo, soi, tna, tsa, iod, ao, nao, pna, wp, sam, pdo.
  - epo: kept through the last-value rule (J2 d); December 2023 is a tail, so its 2023-12 test rows read R30's 0-fill (disclosed). The owner confirms the rule's presence-only reading of later steps (treeroute/io/lastvalue.py).
- soil_organic_carbon_gkg: units unconfirmed (values are in range, so no legal-range problem).

---

Signed: ____________________   Date: ____________

(The loader checks only that this file exists; its content and signature are checked by a later validator.)
