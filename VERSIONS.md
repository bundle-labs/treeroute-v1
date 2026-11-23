# Code versions

This file lists every code version that the paper names (Supplement S4: Tables S4.1 and S4.14, S4.6-S4.8), with
its archive folder, its full hash, the recipe that forms the hash and how the version is rebuilt. Paths are archive
paths. `py -3.9 VERIFY_HASHES.py` recomputes every hash below from the archived files.

A version is either a **full copy** (its files are archived as they were) or an **overlay** (it is rebuilt from a
later version by putting back the files that the later install moved aside; those files are archived too, in the
folders named below). Each overlay version is also written out as a full folder, named "written out" below,
which holds exactly the files that its hash covers; the overlay folders stay in the archive as the record of where
the files came from.

## How the hashes are formed

- **Engine code (treeroute v1 and v2) and report tooling:** the SHA-256 of the canonical JSON of the sorted list of
  [relative path, file SHA-256] over the version's files, the engine's own recipe
  (`engine/treeroute/runs/fingerprint.py`; Supplement S4.1, kind b). For treeroute v1 the files are the engine's
  fingerprinted Python files (94 in 930d961c; the 15 files of `engine/treeroute/_proposed/` are outside).
- **Comment-stripped engine code and engine constants** (Supplement S4.1, kinds c and d): computed by the engine's
  own code, under Python 3.9.13; their values are in `HASH_REGISTER.md`.
- **Common-rival harness:** the SHA-256 of the canonical JSON of [file name, file SHA-256] over `rivals/*.py`; the
  tests are outside the hash.
- **Common-rival export code:** over `export.py`, then `layout.py`.
- **Published-rival tool:** [folder/name, file SHA-256] over `rivals_human/*.py`, then `adapters/*.py`, each list
  sorted as Python sorts the names (a case-insensitive sort gives a different hash); the tool's own recipe is
  `tool_code_sha` in `rivals_code/human_rivals_build/human/rivals_human/common.py`.

## treeroute v1 engine

| Version | Role in the paper | Full hash | Archive folder | How it is rebuilt |
|---|---|---|---|---|
| 7b508557 | PM2.5 run; first NDVI and burned-fraction locks | `7b5085572574d767e7ef13a2248ac03af9e5f103f0ef49f5e85e9994d9344dbb` | `versions/ckpt_20261013/engine_before/treeroute/` (98 files; 83 hashed Python files) | full copy |
| 1f257395 | re-lock 1 (ruling P) | `1f2573957b10b4ddea76bfa38598e35edbc3a593cf2b5eb7b33d1d8e9f386ae1` | `versions/install_20261015/engine_old/treeroute/` (99 files) | full copy |
| 7a0341ef | re-lock 2 (rulings Q, R) | `7a0341eff4e67759bf12542ad5ab0248bf8b2e56d9d2351a30141f67e44f27b8` | `versions/s_20261016/engine_old/treeroute/` (100 files) | full copy |
| 65a177bc | NDVI, burned-fraction and forest-loss runs | `65a177bc7cdd47bacca806582bd13be52706ba3da385bb468fe1f0f24b81a0ff` | written out: `versions/engine_65a177bc/treeroute/` | overlay: start from 930d961c (`engine/treeroute/`); put back the 6 treeroute files of `versions/engine/_moved_coral_20261020_064437/treeroute/`, then the 13 of `versions/engine/_moved_coral_20261020_014111/treeroute/`; remove the 9 files that the coral install added: `check/table.py`, `derive/table.py`, `labels/rows.py`, `package/table.py`, `pipeline/table_ladder.py`, `pipeline/table_passes.py`, `pipeline/table_router.py`, `pipeline/table_run.py`, `route/neighbour.py`. Result: 85 files |
| dd7c0984 | installed, never locked (Supplement S4.3) | `dd7c0984d3044aac6cf06d7614df7bd7e8622942580a5f1f0bb08c32ed085d38` | written out: `versions/engine_dd7c0984/treeroute/` | overlay: 930d961c with the 6 treeroute files of `versions/engine/_moved_coral_20261020_064437/treeroute/`. Result: 94 files |
| 930d961c | coral bleaching run; the reference version | `930d961cdfdd219c36b113174e6c865096f973068e30696850f13d5ec4a60814` | `engine/treeroute/` | the archived engine |

The two install records are `versions/engine/_moved_coral_20261020_014111/INSTALL_MANIFEST.json` (the install of
dd7c0984) and `versions/engine/_moved_coral_20261020_064437/INSTALL_MANIFEST.json` (the install of 930d961c).

## Report tooling (`treeroute_report`)

| Version | Role in the paper | Full hash | Archive folder | How it is rebuilt |
|---|---|---|---|---|
| f3832db1 | the locks before re-lock 3 | `f3832db1896dac4a6962193ea66fbe37cc2f1ea9be3c7c8d10eca8a4bbc4d049` | written out: `versions/report_tooling_f3832db1/treeroute_report/` | overlay: `engine/treeroute_report/` with `table.py` (7125fa63) and `continuity_groups.yaml` (1b1ccef3) from `versions/_moved_nested_treeroute_20261015/treeroute_report/treeroute_report/` |
| af64f5f0 | the deciding NDVI, burned-fraction and forest-loss locks | `af64f5f013ad194fc5aad3bdc7aa99c22ae90941e24e4353105df9f38299d178` | written out: `versions/report_tooling_af64f5f0/treeroute_report/` | overlay: `engine/treeroute_report/` with `table.py` (cfb8e99f) from `versions/engine/_moved_coral_20261020_014111/treeroute_report/table.py` and the same `continuity_groups.yaml` (1b1ccef3) |
| 1658e0dd | the coral bleaching lock | `1658e0ddcf7039e6939fb7ad812885297e025682cf15f29d854d5d98da4b3762` | `engine/treeroute_report/` | the archived report tooling |

## treeroute v2 (the post hoc alarm replay only; Supplement S5)

| Version | Role in the paper | Full hash | Archive folder | How it is rebuilt |
|---|---|---|---|---|
| 88f4db2c | current build; the post hoc replay only | `88f4db2ce7c0a48834243b8e9403a29d8a3dbcc88c00ed44620d9ced79b44b7d` | `versions/engine_v2/engine/treeroute/`, with `treeroute_report/`, `tools/`, `tests/` and `legacy_harness/` beside it | full copy |
| 663ab8ef | second build, before ruling AF2 | `663ab8ef0a666edc786339f2b9e4edac9e067751f72f99ed6a229b903a04bbc3` | written out: `versions/engine_v2_663ab8ef/treeroute/` | overlay: 88f4db2c with the files of `versions/engine_v2/_moved/pre_af2_20261021/engine/treeroute/` |
| fc051e5a | first build, before the review fixes | `fc051e5ae25177e0bc1ed6003f7d0869eac4e25761b7262f94941a10ca963f6e` | written out: `versions/engine_v2_fc051e5a/treeroute/` | overlay: 663ab8ef with the files of `versions/engine_v2/_moved/pre_skeptic_fixes_20261021/treeroute/`; the value is also in that folder's `ENGINE_HASH_BEFORE.txt` |

The three v2 values are recorded in `versions/engine_v2/ALARM_REPORT.txt`; its specification is
`versions/engine_v2/SPEC_ALARM.txt`.

## Common-rival harness and export code

| Version | Role in the paper | Full hash | Archive folder | How it is rebuilt |
|---|---|---|---|---|
| harness 46d0306a | the signed common-rival protocol; the first coral board (refused at score) | `46d0306af3b67f15edf36d8c1fd6ac5e47a1fac06bdf33548b9c88f4decc9485` | written out: `versions/harness_46d0306a/rivals/` | overlay (1 file): `rivals_code/rivals_build/rivals/*.py` with `harness.py` from `versions/rivals_build/_moved/20261021_160025_preUnseenFix/` |
| harness 71457aa9 | the coral and burned-fraction common boards (ruling AG5) | `71457aa902d30dde17a4a88e8d5c7f1de85515c70d2d7ac4745967066f243b97` | written out: `versions/harness_71457aa9/rivals/` | overlay (1 file): `rivals_code/rivals_build/rivals/*.py` with `harness.py` from `versions/rivals_build/_moved/20261022_070259_preLegalFix/` |
| harness b6ea97b7 | the PM2.5, forest-loss and NDVI common boards | `b6ea97b72b5a8f79f7f8257f1e4afd00d7783479fada03eea9101410fa509bf2` | `rivals_code/rivals_build/rivals/` (6 Python files) | the archived harness |
| export code b9243709 | all five common boards | `b92437095456333c187567fb8db0787baaa0f5ed1a33d6540190e0198cc98f4d` | `rivals_code/rivals_build/rivals/export.py` and `layout.py` | the archived code |

## Published-rival tool

| Version | Role in the paper | Full hash | Archive folder | How it is rebuilt |
|---|---|---|---|---|
| tool 32ec5df0 | the Part A signature; the coral, forest-loss and PM2.5 published boards | `32ec5df06e8022be17393cbd1e6fa2e0929876a1f9835a8b8e707761a13133a5` | written out: `versions/rival_tool_32ec5df0/` (`rivals_human/`, `adapters/`) | overlay: cd956f1d with `rivals_human/refs.py` from `versions/human_rivals_build/_moved/refs.py.before_offset_fix_20261025` |
| tool cd956f1d | the NDVI published board and the join | `cd956f1dbd0f9b0f2ada37c1a27f8212768d94fc6242cab0686bf7c71608a273` | written out: `versions/rival_tool_cd956f1d/` (`rivals_human/`, `adapters/`) | overlay: `rivals_code/human_rivals_build/human/rivals_human/` and `adapters/`, with `rivals_human/maps.py` from `versions/human_rivals_build/_moved/20261025T194657Z_partB_baseline/rivals_human/` and without the 5 adapters `fire_*.py` |
| tool 16a2d736 | the Part B files (never run) | `16a2d7362b83d7d8ddf539a5fe4b75f8166fa56976be3f13d88770fbfd68f591` | written out: `versions/rival_tool_16a2d736/` (`rivals_human/`, `adapters/`) | overlay (1 file, renamed): `rivals_code/human_rivals_build/human/rivals_human/` and `adapters/`, with `adapters/fire_geff.py` (33fd951a) from a backup copy (Supplement S4.7.2), file 3fc1fef73679776f@v1, archived as `versions/rival_tool_16a2d736/adapters/fire_geff.py` |
| tool 6a635858 | the Part B files (never run) | `6a6358588fa28db55a0ec819002ebbfd53867e0fd17ea76e912b640fd0e1490a` | `rivals_code/human_rivals_build/human/rivals_human/` and `adapters/` | the archived tool |

`versions/human_rivals_build/_moved/` keeps the tool's moved-aside files with their project-relative paths.

## Registries and configurations of the published-rival tool

- **As archived** (each equals Table S4.14), in `rivals_code/human_rivals_build/human/registry/`: `_schema.yaml`
  0d4dbcb7, `_products.yaml` c7f1ff03, `fire.yaml` bf0b8e55, `coral.yaml` 7e356d61, `defo.yaml` fe11acf4, `pm25.yaml`
  5fe8e221 and `ndvi.yaml` b69537fc; in `rivals_code/human_rivals_build/human/`: the production configuration
  `human_rivals_production.yaml` 0314e9a2 and the DRY configuration `human_rivals_DRY.yaml` 64ce27ca.
- **The copies at the signing time:**
  - `_schema.yaml` a3cda623: `rivals_code/human_rivals_build/pt/ag/full1/grid_ok0/_registry_dry/_schema.yaml`;
  - `_products.yaml` 4e479759: `versions/human_rivals_build/_moved/20261025T194657Z_partB_baseline/registry/_products.yaml`;
  - `ndvi.yaml` e24195f1: a backup copy (Supplement S4.7.2), file a6668f3b53ecbce0@v2, archived as
    `versions/rival_tool_registry_part_a/ndvi.yaml`.
