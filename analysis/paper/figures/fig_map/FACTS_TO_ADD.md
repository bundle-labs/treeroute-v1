# Facts to add: study-region map (Figure 1)

REGISTERED 2026-11-10 in paper/PAPER_FACTS.md, section 4.6: F1-F3 = D57, F4 = D58, F5 and F7 = D59, F6 = D60, F8 = D61 (copied verbatim; the caption cites the D IDs and fig_map.py checks their needles). F9 lists drawing parameters, not data, and stays here. This file is kept as the record the facts were copied from. <!-- Round 4 (2026-11-11): figures renumbered by first citation: map (unnumbered) -> 1, 1 -> 2, 2 -> 3, 3 -> 4, 4 -> 5 (folders keep their names; paper/figures/FIGURE_NUMBERS.md). -->

What fig_map.py checks: every value in F1-F8 was recounted read-only on 2026-11-10 and is asserted by the script (its EXPECT table), except the values marked "read once, not asserted"; the script also checks that this file states the key values (FTA_PHRASES) and names no tool. F9 lists drawing parameters, which are constants of the script; its colour-difference numbers were computed once with a separate colour check and are not asserted. Columns read: region, lat, lon of the four static tables; unit_id, group, lat, lon, mark of the coral lead-0 file; site_key, group, lat, lon, mark of visits.parquet. No label, sea-temperature or answer column was read (ruling AT7). Existing facts the caption cites: D1, D5, D10, D20, D24, D32, D42, D46, D51, D52, K1, M6, P11 (needles checked by the script).

## F1. Region membership combinations (133 panel regions)
- pm25+ndvi 60; pm25+ndvi+defo 28; pm25+ndvi+fire 26; pm25+ndvi+fire+defo 13; ndvi only 4; ndvi+fire 1; ndvi+defo 1 (sum 133).
- Every PM2.5, burned-fraction and forest-loss region is one of the 133 NDVI regions.
- Sources: distinct `region` values of engine/datasets/pm25/data/static/part-0.parquet (127), engine/datasets/ndvi/data/static/part-0.parquet (133), engine/datasets/fire/data/static/part-0.parquet (40) and D:/defo_features/static/part-0.parquet (42).
- Method: for each NDVI region, the list of problems whose static table holds that region, counted by list.

## F2. The map's four categories (by burned fraction and forest loss)
- Burned fraction and forest loss 13; burned fraction only 27 (26 + finnish_lapland); forest loss only 29 (28 + tierra_del_fuego); neither 64 (60 + the four NDVI-only regions).
- Checks: 13 + 27 = 40 (D20, D24); 13 + 29 = 42 (D42, D46); 13 + 27 + 29 + 64 = 133 (D5, D32).
- Source and method: F1, grouped by membership of the fire and defo static tables.

## F3. The six regions without PM2.5 (D10's "6 polar or edge regions")
- alaska_north_slope, canadian_arctic_nunavut, taimyr_peninsula, yamal_peninsula: NDVI only.
- finnish_lapland: NDVI and burned fraction. tierra_del_fuego: NDVI and forest loss.
- Caption display names: Alaska North Slope, Canadian Arctic (Nunavut), Taimyr Peninsula, Yamal Peninsula, Finnish Lapland, Tierra del Fuego.
- Method: NDVI regions minus PM2.5 regions (F1 sources).

## F4. Locations behind the footprints, footprint geometry and the clipping to the coastline
- PM2.5 and forest loss use exactly the NDVI locations of their regions (2,034,972 and 591,809 locations). Burned fraction uses a subset in 26 of its 40 regions, at least 97.0% (minimum 0.9704) of the NDVI locations in each: 925,737 of 929,533 overall. So the map draws every footprint from the NDVI locations.
- Method: join on (region, lat, lon) rounded to 6 decimals; no PM2.5, burned-fraction or forest-loss location is missing from the NDVI table; locations counted per region.
- Footprint = the 0.25° pixels holding at least one NDVI location of the region: 38,207 occupied pixels (38,469 region-pixel pairs). 262 pixels belong to two regions (never more), in 13 pairs; the largest overlap is australian_mulga with brigalow_belt (168 pixels).
- Clipping: each footprint pixel is cut into 8 x 8 cells of 1/32° (about the panel's 4 km spacing), and a cell is drawn when its centre lies inside a GSHHG 2.3.7 low-resolution level-1 polygon (F8). Only the sea clips; lakes do not. 71 regions keep every cell; the least kept are falkland_islands 0.516, greece_mainland 0.704, western_scotland 0.765, tongass_alaska 0.775 and new_zealand_north_island 0.790 (share of cells kept). falkland_islands keeps 1,486 of its 2,880 cells. Method: an even-odd scanline fill of the level-1 rings at the cell centres (exact for the centres).
- Drawing order: larger footprints (more 0.25° pixels) first, so a smaller overlapping region stays on top. After the clipping, every region shows at least 0.830 of its drawn cells; the least is australian_mulga (under brigalow_belt).
- Region extent (NDVI locations): median 3.04° latitude by 4.02° longitude, maximum 9.04° by 12.00°; latitudes -55.00 to 75.02; no region crosses the antimeridian. Smallest short side: namib_desert 0.75°, falkland_islands 0.95°, okavango_delta 1.02°, brittany_france 1.20°, sundarbans 1.43° (all in "neither"); smallest textured region: tongass_alaska (forest loss only), 1.52°.

## F5. Coral bleaching reef sites drawn
- 8,131 distinct reef sites in the 83 kept coral bleaching regions: 7,065 in the 37 scored regions, 1,066 in the 46 training-only regions. 1,262 of the 8,131 have at least one test survey visit.
- The 1,066 equals the header of engine/datasets/coral/split.yaml: "1,874 train visits (1,066 sites".
- The 11 excluded regions hold 44 lead-0 rows at 26 reef sites, not drawn.
- Source: D:/treeroute/coral_build/coral_store/20261020_014201/lead_0.parquet (the path engine/datasets/coral/dataset.yaml gives for lead 0), columns unit_id, group, lat, lon, mark: 13,694 rows in 94 regions (D51); the 83 kept regions hold 13,650 rows, 11,338 train and 2,312 test (D52). Kept and excluded lists: split.yaml.
- Method: a reef site is the package's unit_id, its key_unit '<ecoregion id>_<lat>_<lon>' at 4 decimals (K1). Each unit_id has one position and one region, unit_ids and positions (lat, lon at 6 decimals) are one-to-one, and every unit_id ends in its own lat and lon at 4 decimals. A scored region is a kept region with at least one test-marked lead-0 row (37; D52). Every reef site is one site_key of D:/treeroute/coral_build/coral_data/visits.parquet in the same region. Reef-site latitudes -28.16 to 34.10. fig_map_data.csv gives the unit_id as site_id.

## F6. visits.parquet versus the coral package (why the map reads the lead-0 rows)
- visits.parquet holds 14,839 survey visits (D51) at 8,572 site keys in 97 regions: the 83 kept, the 11 excluded, and 3 on neither list of split.yaml (Darwin, north Australia; Easter Island, south central Pacific; South Java).
- In the 83 kept regions its marks are train 12,168, test 2,581 and unused 38.
- Gulf of Thailand has 10 test-marked survey visits (219 train, 2 unused) in visits.parquet but 152 train rows and no test row in the lead-0 file. Taking visits.parquet's marks would therefore give 38 scored regions, not D52's 37.
- The kept regions have 8,533 reef sites with a train or test visit in visits.parquet, 402 more than the 8,131 the package uses.
- Method: counts of visits.parquet columns group, mark, site_key, lat, lon (reef sites as distinct lat, lon at 6 decimals); Gulf of Thailand compared with its lead-0 rows.

## F7. Reef sites under the regions (the regions are drawn above the dots)
- 229 of the 8,131 reef-site centres lie in a drawn region (after the clipping): florida_everglades 188, pearl_river_delta 24, yucatan_peninsula 9, vietnam_central_highlands 6, new_guinea_papua 1, caatinga 1.
- By coral bleaching region: Bahamas and Florida Keys 188 of its 2,848 reef sites; Hong Kong 24 of 80 (30%, the largest share); Belize and west Caribbean 9 of 598; South Vietnam 6 of 39; Bismarck Sea, New Guinea 1 of 25; Brazil 1 of 109. No other coral bleaching region has a covered reef site. The script stops if any coral bleaching region has more than half of its reef sites covered.
- For comparison, 1,062 before the clipping (whole 0.25° pixels), all 80 of Hong Kong's among them: that coral bleaching region was hidden under pearl_river_delta.
- Method: a reef site is covered when its 1/32° cell is a drawn cell of a region (F4); no reef site lies under two regions, and none under an open outline. The caption states 229, the 188 "in south Florida" and Hong Kong's 24 of 80. Listed per reef site in fig_map_data.csv (column covered_by_region). A covered dot (1.7 pt, about 1.2° at the map scale) still shows wherever it reaches past the region's edge.

## F8. Coastline input
- GSHHG 2.3.7: README.TXT says "Version 2.3.7 June 15, 2017" and "Distributed under the Lesser GNU Public License"; LICENSE.TXT says GSHHG is distributed under the GNU Lesser General Public License (LGPL) version 3 or later (from GSHHG 2.2.2 on).
- Low resolution, all polygons, read and counted: level 1: 5,706 records (land and ocean boundary; drawn, and the only level that clips the regions); level 2: 4,367 records (lakes); level 3: 506 records (islands in lakes); level 4: 11 records (ponds on those islands).
- Lakes (levels 2-4) are not drawn, as the figure brief named level 1 only, and the caption says "Lakes are not drawn." The Caspian Sea and the large lakes therefore show as land. For the lead to decide: setting LAKES = True in fig_map.py draws them (lakes white, islands in lakes as land, ponds white) and the script then requires the credit "Coastlines and lakes: ..." without "Lakes are not drawn." in the caption. Against it: README.TXT says the lake polygons derive from WDBII, an older database, so the Aral Sea is drawn at its full former extent (level-2 polygon id 5837, area 67,543 km² in the attribute table GSHHS_l_L2.dbf; read once, not asserted), about 2 mm across at print, where today's lake is far smaller.
- Source: D:/coral/drivers/gshhg/gshhg-shp-2.3.7.zip, read in memory with Python's zipfile module and a struct-based shapefile reader; nothing was extracted.
- Licence note for the lead: LICENSE.TXT also asks that the copyright and permission notice appear in all copies of the data and its documentation. The figure is a rendering, not a copy of the data; the caption's credit names the source, version and licence. README.TXT's history note for version 2.2.2 says the data are "now released under the lesser GNU License, v3 or any earlier version", while LICENSE.TXT says "version 3 or later"; the caption follows LICENSE.TXT.

## F9. Drawing parameters (not data; listed because the caption and image show them)
- Equirectangular projection (x = longitude, y = latitude, one scale), cropped to 180°W-180°E and 60°S-80°N; graticule every 30°, labelled 60°N, 30°N, 0°, 30°S and 120°W, 60°W, 0°, 60°E, 120°E.
- Figure 190 x 88.7 mm (Elsevier full width); map 180.5 x 70.2 mm, 0.501 mm per degree. The figure is laid out and its text measured at 300 dpi, the resolution of the PNG.
- Footprint grid 0.25°, clipped on a 1/32° raster (F4). A filled region's white gap (0.35 pt) is drawn only where it meets land or another region. Open outlines 0.7 pt, traced after a closing with a disc of radius 0.5° (16 cells of 1/32°), which bridges gaps and inlets narrower than about 1° (drawing only; no reef site lies under an open outline, and the clipping shares in F4 are measured before this step).
- Textures at 45° (burned fraction) and 135° (forest loss): single lines 0.4 pt, 0.6 mm apart; crossed lines (both) 0.25 pt, 0.7 mm apart, so that each textured category gives about 23.5% of its area to white (23.5% single, 23.6% crossed; the script stops if they differ by more than one point). White on filled regions, in the region's colour on open ones. White rather than a darker tone of each fill, because the palette documents no darker steps for orange and aqua. Reef-site dots 1.7 pt.
- Colours: blue #2a78d6, orange #eb6834, aqua #1baf7a (the reference palette's first three categorical colours, as in Figures 4 and 5), neutral #52514e (secondary ink), land #e8e7e1 (a derived chrome value between the palette's neutral #f0efec and its gridline #e1e0d9; 1.24:1 against the white sea), sea white, graticule #e1e0d9, frame #c3c2b7.
- Colour-difference check (computed once, not asserted; OKLab ΔE x100, colour-vision deficiency by the Machado et al. 2009 simulation at full severity, WCAG 2 contrast), all pairs. Solid fills: worst CVD ΔE 9.2 (aqua vs orange, deutan), worst normal-vision ΔE 24.0 (aqua vs blue); the neutral clears each hue by normal-vision ΔE 21.8 or more and CVD ΔE 18.3 or more; contrast on the land fill: blue 3.56, orange 2.58, aqua 2.27, neutral 6.41. Fills with their white lines averaged in (linear light, as the eye averages a texture it does not resolve): blue #8aa6e1, orange #f09e8c, aqua #87c6a7; worst normal-vision ΔE 14.1 (blue vs aqua), worst CVD ΔE 4.6 (orange vs aqua); contrast on the land fill 1.97, 1.70, 1.59. Before the texture change (crossed lines covering 41.5%) the averaged blue was #afc0e8, worst normal-vision ΔE 11.5 and blue's contrast 1.47. The averaged colours are a worst case: where the lines are resolved, the line direction carries the category.

## Proposed reference entry
README.TXT inside gshhg-shp-2.3.7.zip gives this reference, quoted exactly (its line break and tab joined into one space):

> Wessel, P., and W. H. F. Smith (1996), A global, self-consistent, hierarchical, high-resolution shoreline database, J. Geophys. Res., 101(B4), 8741–8743.

Proposed entry for draft/REFERENCES.md, Section A, in its style:

- **Wessel, P., & Smith, W. H. F. (1996).** A global, self-consistent, hierarchical, high-resolution shoreline database. *Journal of Geophysical Research: Solid Earth*, 101(B4), 8741–8743. — Key `WesselSmith1996_GSHHG`. Supports: the coastlines of Figure 1 (GSHHG 2.3.7, low resolution, level 1). Check: wording from GSHHG's README.TXT; the DOI is not given there and was not checked here (expected 10.1029/96JB00104; the reference check should confirm it against Crossref). Licence: LGPL version 3 or later (LICENSE.TXT).

## Entries outside this folder (for the lead; not edited here)
- draft/REFERENCES.md: add the entry above.
- draft/S9_inputs_licences.md: add a GSHHG row, for example: "GSHHG 2.3.7 shoreline polygons (low resolution, level 1), D:/coral/drivers/gshhg/gshhg-shp-2.3.7.zip; used for the coastlines of Figure 1 and to clip its regions; licence: 'As of GSHHG 2.2.2, GSHHG is distributed under the GNU Lesser General Public License (LGPL) version 3 or later' (LICENSE.TXT; README.TXT's 2.2.2 note says 'v3 or any earlier version'); the copyright and permission notice must travel with copies of the data."
- The availability section (09_availability): name the GSHHG 2.3.7 shapefile zip as an external input that must be downloaded to re-run paper/figures/fig_map/fig_map.py.
