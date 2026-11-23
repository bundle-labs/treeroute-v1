# D4 GADM 3.6: rules the defo build must follow (to pre-register; written 2026-10-21)

These come from the skeptic review of the D4 download. No re-download is needed; the 52 country files are complete
(`D:\treeroute\human_products\gadm\3.6_gpkg_defo42\product_manifest.json`).

1. **Cell-to-unit assignment: by overlap, not by centre.** Assign each defo cell to the level-2 unit it overlaps
   most. If it overlaps none, use the nearest unit within half a cell. Never use "centre inside polygon".
   Why: of the 2,397 coastal cells that touch no unit by their centre, 427 are at least 50% land with forest.
   Their centres fall in rivers or estuaries. Examples: borneo_rainforest 28 such cells holding 181,234 loss pixels;
   western_scotland 58; pacific_nw_coast 47; new_zealand_north_island 47. The cell at (1.347, 110.69) is 0.002 deg
   from the MYS level-2 unit Simunjan; (-33.471, 151.115) is 0.0008 deg from AUS unit Hornsby.
   The build reports how many cells each step assigns (overlap, nearest within half a cell, none).
2. **Level-1 fallbacks.** Two countries have no level 2 in GADM 3.6 (checked in the downloaded GeoPackages):
   - Ireland (`IRL`): layers `gadm36_IRL_0` (1) and `gadm36_IRL_1` (26 counties) only. The whole `ireland`
     region (9,666 cells) uses the 26 level-1 counties.
   - Hong Kong (`HKG`): `gadm36_HKG_1` (18 districts) only; the Hong Kong part of `pearl_river_delta` uses them.
   Both are pre-registered as "level 1 where level 2 does not exist", disclosed in the defo human Part.
3. **Unused countries.** Albania, Azerbaijan, Brunei and Macao were fetched (generous border list) but no defo
   cell needs them (about 1.5 MB). They stay on disk, unused; nothing is deleted.
4. Licence: GADM is free for academic, non-commercial use; no redistribution (https://gadm.org/license.html).
   Do not copy the GeoPackages into any shared export.
