# Rebuilding the inputs

This file says which archived scripts rebuild the inputs of the five problems, in what order the coral bleaching
chain runs, which two rebuild inputs no archived script writes, how the figures are re-drawn, which libraries the
scripts need, and what stays unresolved. Paths are archive paths, except the fixed input paths that the scripts
themselves read, which are quoted as the scripts spell them.

## What the archive can and cannot rebuild

- The archive holds no per-location values of the tree inputs. The inputs stay with their providers, and the
  archived scripts fetch or rebuild them where their sources are recorded.
- Some inputs cannot be rebuilt: the elevation model, the coast-distance product and the SoilGrids release behind
  some tree inputs are "source not recorded" (Table S9.2; ruling AV21), and the MERIT Hydro version, the MOD44B
  version and the GPCC product behind the SPI files are not recorded either (facts L7 and L8; Supplement S9.6,
  item 3).
- Some sources revise their history: each Hansen release re-derives the forest-loss years, and IBTrACS revises its
  best tracks after each season. A rebuild may therefore not match the original files byte for byte.
- None of the engine's fitted trees (specialist trees, correctors and error-weight forests) is archived, so every
  tree must be refit, on the pinned libraries and four threads.
- So the archive alone does not re-run the routing: the tree inputs must first be rebuilt.
- It has not been checked that the archived scripts are the exact versions that built each store. The store
  catalogs' provenance fields name the script behind each store column (for example
  `presplit_cc/assemble_monthly_panel.py:36` in `engine/datasets/_stores/monthly_panel_v170_schema_catalog.yaml`).

## The scripts

`rebuild/` holds the fetch, ingest and assembly scripts for the panel, the targets and the package stores, and every
local module that they import (an import walk of the rebuild scripts, the rival tools and the engine modules they
reach found no other local module):

- the project folder's scripts, at the top of `rebuild/` (27 files): `acag_pm25_ingest.py`, `defo_fetch.py`,
  `defo_ingest.py`, `fire_fetch_target.py`, `fire_build_history.py`, `fire_build_danger.py`,
  `fire_build_ndvi_lags.py`, `fire_join_drivers.py`, `fire_select_cells.py`, `gfed_burn_ingest.py`,
  `edgar_emis_ingest.py`, `panel_sentinel.py`, `all133_regions.txt`, and the coral scripts `coral_fetch_target.py`,
  `coral_fetch_sst_full.py`, `coral_fullscale.py`, `coral_fetch_drivers.py`, `coral_forecast.py`,
  `coral_fetch_sst.py`, `coral_mhw_features.py`, `coral_dhw_model.py`, `coral_extra_drivers.py`, `coral_safe.py`,
  `coral_smoke_rf.py`, `coral_smoke_regress.py`, `coral_glorys2_ab.py` and `coral_architecture.py`;
- `rebuild/presplit_cc/` (36 files: the 35 scripts below and `config.yaml`, see Libraries): `assemble_monthly_panel.py`, `assemble_human_drivers.py`,
  `add_drought_wbal_all_regions.py`, `save_regime_to_panel.py` (with the modules it imports,
  `experiment_regime_stream.py`, `train_small_bundle_regime_thar.py`, `experiment_thar_regime_full.py` and
  `train_small_bundle_wm_thar.py`), `monthly_loader.py`, `download_drivers.py`, `download_drivers_extra.py`,
  `download_drivers_extra2.py`, `download_drivers_extra3.py`, `fetch_env_noauth.py`, `fetch_livestock_extend.py`,
  `fetch_livestock_extract.py`, and the ingest scripts `ingest_agera5_clustered.py`, `ingest_agera5_daycounts.py`,
  `ingest_deeprec_tws.py`, `ingest_drought_indices.py`, `ingest_era5land_extra.py`, `ingest_era5land_snowphen.py`,
  `ingest_era5land_soilmoisture.py`, `ingest_ersst_boxes.py`, `ingest_esacci_sm.py`, `ingest_firecci_fire.py`,
  `ingest_fluxsat_gpp.py`, `ingest_grace_monthly.py`, `ingest_luh3_drivers.py`, `ingest_modis_cmg_local.py`,
  `ingest_modis_ndvi_appeears.py`, `ingest_noaa_indices.py`, `ingest_spei_monthly.py`,
  `ingest_terraclimate_monthly.py` and `ingest_worldpop_annual.py`;
- `rebuild/inputs/coral/events_dated.parquet`, one of the two rebuild inputs that no archived script writes (below).

The rebuild also uses code in other folders: the package ingest and feature scripts (`engine/datasets/<pkg>/ingest/`
and `features/`), the coral table builders (`coral_build/coral_tables/`) and their pinned copies in
`analysis/coral_sens_2017_2020/`, the product fetcher `rivals_code/human_tools/fetch_products.py` and the
published-rival tool's product adapters (`rivals_code/human_rivals_build/human/adapters/`).

Some fetch scripts need an account with the data provider. In `rebuild/`, ten scripts read credentials: six through
the CDS key file that `cdsapi` reads, and four from `~/.netrc`; the product fetcher
`rivals_code/human_tools/fetch_products.py` reads the ADS and EWDS key files (`~/.adsapirc`, `~/.ewdsapirc`). No
credential is archived; a reader uses their own. Only `ingest_worldpop_annual.py` starts
another program (`curl`, to download). No script runs another local script, except stage 1 of `coral_fullscale.py`,
which calls `coral_fetch_sst_full.py` in the same process.

## Coral bleaching, in this order

1. `coral_fetch_target.py`: the Global Coral Bleaching Database labels.
2. Copy `rebuild/inputs/coral/events_dated.parquet` to `D:\coral\target\events_dated.parquet`; the scripts read
   that fixed path (below).
3. `coral_fetch_sst_full.py`, or `coral_fullscale.py --only 1`, which runs it: the full-history CoralTemp sea-surface
   temperatures.
4. `coral_fullscale.py --only 2`: the sea-surface temperature compact `sst_compact_all.npz`, the source that the
   coral catalog cites. Its recorded size and SHA-256, the target of this step: 931,987,766 bytes,
   `361cefd0a437a33a2b880ad08a26cc4ce4c3a08f9bf04249e8c3274a827cb7aa`, recorded in
   `rival_boards/rivals_human/_products/coral_sst_npz/product_manifest.json` and in the coral store's
   `coral_build/coral_store/20261020_014201/build_manifest.json`. The original compact is not in the archive.
5. `coral_fetch_drivers.py`: the Nino-3.4 and DMI indices, the IBTrACS file and the Coral Reef Watch 5 km
   climatology grid; also the MEOW regions and the reef extent layer.
6. **The two legacy feature tables.** Run the `build()` of `coral_forecast.py` for leads 0 and 365, and not its
   `main()`. Run it in the folder that the `ROOT` constant of `coral_build/coral_tables/build_tables.py` names (on
   the run machine, the project folder; put the top-level scripts of `rebuild/` there, or set that constant in a
   copy), because it writes `forecast_features_L0.parquet` and `forecast_features_L365.parquet` into the working
   folder and skips a table that already exists. With Python 3.9 (`-I` keeps the working folder off the import
   path, so the command puts it back):

   ```
   py -3.9 -I -c "import sys; sys.path.insert(0, '.'); import coral_forecast as F; F.build(0); F.build(365)"
   ```

   - It reads the compact of step 4, `events_dated.parquet`, and the indices, IBTrACS and the climatology grid of
     step 5. Its `main()` would also score, and needs `fullscale_split.json`, which only stage 4 of
     `coral_fullscale.py` writes; the rebuild does not run that stage. Importing `coral_forecast` does no work before
     `build()` is called.
   - `build_tables.py` hashes both tables before it starts (`inputs_meta`, lines 428-435, called at line 462), so a
     missing table stops the build. Its proof 4 recomputes the features of the single-sample survey visits at leads 0
     and 365 and compares them with these tables (relative tolerance 1e-9; lines 508-513, 621-622 and 701-740); any
     mismatch stops the build.
   - The two tables are kept out (`KEPT_OUT.md`, D). Their recorded sizes and SHA-256 (in the coral store's
     `build_manifest.json`, under "inputs") are the targets: `forecast_features_L0.parquet`, 5,385,108 bytes,
     `4ef950db3d64062a51bedd70136c14590dd20789f25167209eb8a5e151409c52`; `forecast_features_L365.parquet`, 5,286,267
     bytes, `fa213246fe6df283385814aa01cf2018af54c28de6494463db6d4912b745c0eb`. Both were written with pandas 2.3.3
     and pyarrow 21.0.0, the versions of `environment/requirements_py39_core.txt`. A byte match also needs
     byte-identical inputs, which the IBTrACS and CoralTemp downloads may not give; proof 4, which compares values
     with the rebuilt tables, is the check that decides.
   - Which runs wrote the two targets: the archived script's run of 2026-08-26, started at 07:36:32 UTC, wrote the
     lead-365 table at 08:16:15 UTC; its log, `records/earlier_runs/CORAL_FORECAST.log` (times, counts and aggregate
     scores only), records that it found the lead-0 table present and skipped it. The lead-0 table, written at
     07:30:19 UTC that day, comes from the archived `build()` code.
7. The coral table builders: `coral_build/coral_tables/build_visits.py`, then `build_tables.py`.

Not part of the rebuild: the `main()` of `coral_dhw_model.py`, `coral_mhw_features.py`, `coral_glorys2_ab.py` and
`coral_forecast.py`, and stages 3-5 of `coral_fullscale.py`. They are an earlier experiment whose own inputs no
archived script writes; `coral_fullscale.py` imports only functions from them, and only in those stages.

## Forest loss

`defo_fetch.py` (line 47) and `defo_ingest.py` (line 231) read the forest census `D:\run89full\forest_census.csv`,
and no archived script writes it (fact D46). Copy `records/earlier_runs/forest_census.csv` (14,813 bytes; SHA-256
`ca79ffe48f9438828ef3aae54013bc54d297ca3c7f573af7f9f5432d32a0eeb1`, the hash that the package's `split.yaml` pins)
to that path. When `D:\run89full\forest_region_bbox.csv` (not archived) is absent, `defo_fetch.py` derives it from
the census and the panel's 2010 files.

## The two rebuild inputs that no archived script writes

| Archive path | Copy to (the path the scripts read) | Bytes | SHA-256 | Read by |
|---|---|---:|---|---|
| `rebuild/inputs/coral/events_dated.parquet` (23,258 sample events, 12 columns; fact L13) | `D:\coral\target\events_dated.parquet` | 510,044 | `17f0b641e85c9e3ebc6e36d1ee60a8724f63a894d6f17b271fc9729c80960ed6` | `coral_fetch_sst_full.py` (the sites to fetch), `coral_forecast.py` (its `build()`), `build_visits.py` (a cross-check of coordinates, ecoregion and date per sample) and `build_tables.py` (coordinates for the replay copy) |
| `records/earlier_runs/forest_census.csv` (fact D46) | `D:\run89full\forest_census.csv` | 14,813 | `ca79ffe48f9438828ef3aae54013bc54d297ca3c7f573af7f9f5432d32a0eeb1` | `defo_fetch.py`, `defo_ingest.py` |

## Re-drawing the figures

The figure scripts read their inputs at project paths. To re-draw from a copy of the archive:

- Make a working folder that holds `engine/` (from the archive), `paper/figures/` (a copy of
  `analysis/paper/figures/`) and `paper/PAPER_FACTS.md` (a copy of `records/fact_sheet/PAPER_FACTS.md`). Run
  `fig_map.py` with `--root <that folder>`; `ga.py` takes the same root from its own path.
- In a copy of `fig1.py` and `fig2.py`, set the constants that name the run machine's project folder to that folder.
  `fig2.py`, `fig3.py` and `fig4.py` read `D:/treeroute/runs/...`: place the archive's `runs/` at
  `D:/treeroute/runs`, or point the scripts at it, in which case their data files record the new input paths.
- `fig_map.py` also needs four inputs that the archive does not hold, at the paths it names: the GSHHG 2.3.7
  shapefile zip (`D:\coral\drivers\gshhg\gshhg-shp-2.3.7.zip`, from its provider); the coral store's `lead_0.parquet`
  in the stamp folder `coral_store\20261020_014201\` that `fig_map.py` and the coral package's `dataset.yaml` name (a
  rebuilt store is published under a new stamp, so it must be placed there); the coral tables' `visits.parquet`
  (both rebuilt by the coral chain above); and `D:\defo_features\static\part-0.parquet`.
- `fig1.py` and `ga.py` also read paper texts that the archive does not hold (the draft of the paper's Section 2,
  and the drawing brief of the graphical abstract), so they cannot run their checks from the archive alone. Their
  outputs, data files and captions are archived.
- The libraries are those of `environment/requirements_py312_figures.txt` (Python 3.12.10).
- What a re-draw reproduces (measured on 2026-11-11 from copies): every PNG comes out byte for byte, and so do the
  data files, except that `fig1_data.csv` and `fig2_data.csv` record the path constants, so they differ once those
  are set, and that `fig2_data.csv`, `fig3_data.csv` and `fig4_data.csv` record the `D:/treeroute/runs` input paths,
  so they differ too unless the archive's `runs/` is placed at `D:/treeroute/runs`; `ga.pdf`, `ga.tif` and the two
  renders of the graphical abstract come out byte for byte; the other PDFs differ in their creation date, and
  `fig1.pdf` to `fig4.pdf`, drawn on the run machine before its reinstall, also in their embedded font data, where
  the system's Arial differs.

## Libraries

- **The engine, the rival tools and the rebuild scripts:** Python 3.9.13 with `environment/requirements_py39_core.txt`:
  the 15 fingerprinted libraries of every run (numpy 2.0.2, scipy 1.13.1, scikit-learn 1.6.1,
  scikit-learn-intelex 2025.10.0, daal 2025.10.0, tbb 2022.3.1, pandas 2.3.3, pyarrow 21.0.0, threadpoolctl 3.6.0,
  pydantic 2.13.3, pydantic-core 2.46.3, typer 0.23.2, click 8.1.8, PyYAML 6.0.3, psutil 7.2.2), their dependencies,
  and the libraries of the rival boards, the post hoc tools and the fetch scripts (among them xarray 2024.7.0,
  netCDF4 1.7.2, h5py 3.14.0 and lightgbm 4.6.0). `environment/check_env.py` checks an installed environment.
- **The full test suite of the published-rival tool, and the rebuild scripts that read rasters, vector layers or
  cloud files:** `environment/requirements_py39_fullsuite.txt` (rasterio 1.4.3, geopandas 1.0.1, shapely 2.0.7,
  pyogrio 0.11.1, pyproj 3.6.1, fsspec 2025.10.0 and the other dependencies of torch 2.8.0+cu128, which is installed
  separately from the PyTorch index). The file's header calls it optional, for the full test suite only, but
  rasterio is imported by `defo_ingest.py`, `fire_fetch_target.py`, `fire_join_drivers.py`,
  `presplit_cc/assemble_human_drivers.py`, `presplit_cc/fetch_env_noauth.py`, `presplit_cc/ingest_drought_indices.py`
  and (optionally) `presplit_cc/fetch_livestock_extend.py`, and reached through imports by `fire_select_cells.py`
  and `presplit_cc/ingest_worldpop_annual.py`; `presplit_cc/assemble_human_drivers.py` also needs pyogrio and
  geopandas (`pyogrio.read_dataframe` returns a GeoDataFrame), and `acag_pm25_ingest.py` needs fsspec.
- **The figures:** Python 3.12.10 with `environment/requirements_py312_figures.txt` (matplotlib 3.11.0, numpy 2.5.0,
  pandas 3.0.3, pyarrow 25.0.1, pillow 12.2.0 and their dependencies).
- **No version recorded:** requests, cdsapi and catboost (the NDVI regime classifier behind
  `save_regime_to_panel.py`), and three libraries that are needed through calls, not imported by name: s3fs
  (`acag_pm25_ingest.py` reads a public S3 bucket through fsspec), dask (`presplit_cc/assemble_human_drivers.py`
  opens one NetCDF file in chunks) and openpyxl (the same script reads one .xlsx file; it catches each driver's
  error and prints FAILED, so a missing library leaves that driver's columns out instead of stopping the run).
  `ingest_modis_cmg_local.py` imports pyhdf, which the run machine kept in a separate conda environment
  (pyhdf 0.11.6, Python 3.11.15). `ingest_worldpop_annual.py` runs the `curl` program.
- **`rebuild/presplit_cc/config.yaml`:** the project's paths and settings, which `monthly_loader.py`,
  `assemble_monthly_panel.py` and most ingest scripts read when they start. Its folder paths are those of the run
  machine (user names replaced); set them to your own folders before a rebuild.
- The two requirement files of Python 3.9.13 hold the exact libraries of the run machine, from the run manifests and
  its package records; they do not show which version built each store.

## Unresolved

- `tier1_climate_indices.py`, which `engine/datasets/_stores/INDEX_WINDOW_AUDIT.md` cites, is not in the archive and
  was not found in the project folders. The audit cites it for index columns that are not in the panel, so no
  rebuild needs it.
- `yearclock.py`, cited as a scratch script in the burned-fraction and forest-loss ban lists
  (`engine/datasets/fire/ban.yaml` line 750, `engine/datasets/defo/ban.yaml` line 269, and their drafts), and
  `yearclock_screen.py`, cited as a scratch script in `engine/datasets/fire/ban.yaml` (lines 1222 and 1264) and its
  draft, are not in the archive and were not found in the project folders.
- The package catalogs and ban lists also cite 14 earlier scripts of the project folder as evidence for ban-list
  calls and legacy rules. They are outside the scripts that the rebuild imports and are not in the archive:
  `adaptation.py`, `defo_ablate.py`, `defo_ban.py`, `defo_matrix.py`, `fire_architecture.py`,
  `fire_ban.py`, `fire_evt_arch.py`, `pm25_adaptation.py`, `pm25_architecture.py`, `pm25_ban.py`, `pm25_split.py`,
  and, in `presplit_cc/`, `bundle_lag_compare.py`, `cross_region_run89.py` and `run89_outputs.py`.
