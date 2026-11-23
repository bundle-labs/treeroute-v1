# S8: the 17 refreshed disclosures, in short (for the owner to read before signing)

Ruling N S8: these 17 exceptions.yaml entries are signed only after you read them. They are drafted, NOT signed and NOT
installed. Draft copies: `D:/treeroute/apply_20261006/s8_refresh/<package>/exceptions.yaml` (made from the packages
after the sign-off apply; every other entry is unchanged). Each refresh only writes down rulings already made (L1, L3, N).
The other 28 entries were signed by the apply (ruling N S8).

| # | Entry | Old meaning | New meaning |
|---|---|---|---|
| 1 | PM2.5 3, epo | Kept; December filled from November; its window still waits for your signature; a 2023-12 test row reads a zero-fill. | Window signed (L1 b), so it is lagged 1 month. Each December is filled from November and read by the January after it. No test row reads the missing December 2023. The "fill needs January present" reading is signed (L1 d) and disclosed. |
| 2 | PM2.5 5, aglw_cattle | Raw livestock kept as watch; the fake 2022 layer (India's growth applied everywhere) IS read by 2023 test rows; the fix is your open decision. | Raw column banned and never read (L3, reason incomplete S13). Its hold column (the real 2021 layer carried into 2022-23) replaces it, lagged 1 year, so 2023 rows read a real layer two years old. |
| 3 | PM2.5 6, aglw_buffalo | Same as 2. | Same as 2. |
| 4 | PM2.5 7, aglw_horse | Same as 2. | Same as 2. |
| 5 | PM2.5 8, aglw_sheep | Same as 2. | Same as 2. |
| 6 | PM2.5 9, aglw_goats | Same as 2. | Same as 2. |
| 7 | PM2.5 10, aglw_total_lsu | Same as 2. | Same as 2. |
| 8 | fire 1, livestock | The six raw livestock columns are watch (fire never reads 2022-23 anyway). | Raw columns banned, hold columns watch (L3). On fire the hold equals the raw value on every row it reads, so nothing changes in practice. |
| 9 | defo 8, lineage check | The lineage check skips the K-store columns; you choose among three fixes; the livestock parents' word "incomplete" was called a workaround. | Kept as is (S16): the K3/K5 keeps stand, reason words stay, no engine change. "incomplete" is now your confirmed word (S13), not a workaround. |
| 10 | NDVI 5, snow_cover_fraction | Watch, but the polar-night choice (keep, ban or hold out) is open. | Watch chosen (S15). In 5 Arctic groups, winter gaps longer than 2 months are read as "no snow". Disclosed; no leak either way. |
| 11 | NDVI 6, epo | Kept with December filled; the window is unsigned (refused); the "fill needs January present" reading is asked of you. | Window signed (L1 b), lagged 1 month. The reading is signed (L1 d) and disclosed. |
| 12 | NDVI 10, aglw_cattle | Raw livestock kept as watch; the fake 2022 layer is read by 2023 rows. | Raw column banned and never read (L3, S13). The hold column replaces it, lagged 1 year: 2023 rows read the real 2021 layer, 2020-22 rows are unchanged. |
| 13 | NDVI 11, aglw_buffalo | Same as 12. | Same as 12. |
| 14 | NDVI 12, aglw_horse | Same as 12. | Same as 12. |
| 15 | NDVI 13, aglw_sheep | Same as 12. | Same as 12. |
| 16 | NDVI 14, aglw_goats | Same as 12. | Same as 12. |
| 17 | NDVI 15, aglw_total_lsu | Same as 12. | Same as 12. |

To sign after reading: install the draft files (move the current ones aside), then run
`py -3.9 datasets/_tools/apply_signoff.py datasets/_tools/signoff_answers_2026-10-06.yaml` with the S8 `sign_only` list
widened to these 17 entries (the dry run shows each entry before it is signed), then `--apply`.
