# Defo: 5 new disclosures to sign (drafted 2026-10-07, NOT signed)

They are entries 10-14 of datasets/defo/exceptions.yaml. Each records a ruling-N change you already made. Defo's freeze waits until you sign them.

1. S1: the three scPDSI columns are banned, because scPDSI can change a month's value after later months are known.
2. S3: the four MODIS land-cover columns are banned, because their labels are smoothed across years, so a lag does not clean them.
3. S6: last year's NDVI/EVI reach at most 3 days, and albedo/GPP at most 8 days, into the predicted year. You accepted this.
4. S6: population_density is lagged 1 year, as a precaution like the livestock layers (J3). No leak had been measured.
5. S28: phenology enters only as its value from 2 years back, because the 1-year-back value still overlaps the predicted year.

To sign: say "sign the 5 defo disclosures". An agent then replaces "UNSIGNED" with your signature, re-runs `check` and `check --deep` on defo, and freezes defo alone.
