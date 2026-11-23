# treeroute v1: engine, rival tools and scripts for five environmental forecasting problems

This archive holds the code, the written rules, the run records and the row-level predictions behind the paper
"Ridge weighting of other regions' regression trees, anchored to the seasonal normal: a temporal hold-out test on
five environmental forecasting problems", by Mohammed Nadir Benkaddour. The five problems are PM2.5, NDVI, burned
fraction, forest loss and coral bleaching; in folder and file names they are `pm25`, `ndvi`, `fire`, `defo` and
`coral`.

The method's engine is treeroute v1. Its reference version is **930d961c**, the hash of the engine's code
(`engine/treeroute/`), which made the coral bleaching run and which every rival board pins. The other two run
versions are 7b508557 (PM2.5) and 65a177bc (NDVI, burned fraction and forest loss); small check runs gave
byte-identical outputs across the versions. This release is version 1.0.0; the engine's own version
label still reads '0.0.1-skeleton' (see "Known documentation issues").

**Two linked records.** The archive is published as two Zenodo records, linked to each other: the code's record,
made from a release of the GitHub repository (https://github.com/bundle-labs/treeroute-v1; DOI 10.5281/zenodo.24452866), and the
data record "treeroute v1: run records and row-level predictions for five environmental forecasting problems" (DOI
10.5281/zenodo.24452794), which holds the run records and the row-level predictions. The GitHub repository
holds the code and the key text records: no file of 25 MiB or more, and no Parquet, image or PDF file except the
three static location tables of the dataset packages. The data record holds the whole archive, the code included,
as 15 zip files beside the root files, so that it can be checked on its own: unzipped into one folder, the zips give
the folder tree below, and `VERIFY_HASHES.py` and `SHA256SUMS.txt` check it. The last column of the table says which
files the GitHub repository holds as well.

## Folders

| Folder | What it holds | Licence | In the GitHub repository |
|---|---|---|---|
| `engine/` | The reference engine 930d961c (`engine/treeroute/`), its report tooling 1658e0dd, its tests, the five dataset packages and their drafts, the shared store catalogs, the signing tools and the review evidence; the author's rulings, the project log (`PENDING_PARTS.md`, cited as "Part N"), the protocol drafts, the plans and the README; `README_ARCHIVE.md` | MIT | yes, except three draft static tables (byte-identical to the live ones) |
| `versions/` | Every earlier engine, report-tooling, treeroute v2, harness and published-rival tool version that the paper names: full copies, the files that rebuild the others, and the rebuilt versions written out (`VERSIONS.md`) | MIT | yes |
| `rivals_code/` | The common-rival harness b6ea97b7 with its tests, specifications, protocol draft and no-op evidence; the published-rival tool 6a635858 with its adapters, registries, configurations, tests and specifications; the product fetcher with its reports and site-day lists; the research notes for the published rivals | MIT | yes |
| `coral_build/` | The coral table builders, the coral report script, the coral signing tool and its records, specifications, no-op scripts and synthetic toy tests; the record files of the coral table build (build manifests, the visit census, check reports and build logs) | MIT for the scripts, CC BY 4.0 for the data and records | yes, except the toy Parquet files |
| `rebuild/` | The fetch, ingest and assembly scripts for the panel, the targets and the package stores, the coral input chain, every local module they import, `all133_regions.txt`, and the coral rebuild input `inputs/coral/events_dated.parquet` (`REBUILD.md`) | MIT; CC BY 4.0 for `inputs/` | yes, except the Parquet file |
| `environment/` | The exact library pins (`requirements_py39_core.txt`, `requirements_py39_fullsuite.txt`, `requirements_py312_figures.txt`) and the environment check `check_env.py` | MIT | yes |
| `analysis/` | The figure scripts with their data, outputs and captions (`analysis/paper/figures/`); the post hoc analyses (Parts 601-604, 611-612, 622-625, 627 and 628), among them the SHAP comparison (`analysis/shap_v1/`) and its table build (`analysis/paper/supp_build/s3_13/`); the table scripts | MIT for the scripts, CC BY 4.0 for the data | yes, except the Parquet results and the images |
| `records/` | The frozen fact sheet (`records/fact_sheet/PAPER_FACTS.md`); the locks, protocol copies, signature records and verification records (`records/registry/freeze/`, with a dated note beside each of the four gridded protocol copies); the signed rival protocols (`records/registry/rivals/`); the input-store register; the superseded check reports; the seven project documents that the fact sheet cites (`records/project_docs/`); the earlier runs' documents, scripts and evidence (`records/earlier_runs/`); and the paper checks (`records/paper_checks/`) | CC BY 4.0; MIT for the scripts | yes |
| `runs/` | The five headline run folders (coral bleaching without its per-visit Parquet files), the headline tables and the deciding check reports | CC BY 4.0 | the headline tables and check reports only |
| `rival_boards/` | The five common-rival boards (coral bleaching: records only), the four published-rival boards (forest loss and coral bleaching: records and aggregate scores only), the PM2.5 published rivals' MERRA-2 index tables, the product manifests, both rival ledgers and both joined rival tables | CC BY 4.0 | the ledgers and joined tables only |
| `evidence/` | The no-op proofs (small check runs under the old and the new engine at each engine change), three NDVI run folders made under superseded locks, and the treeroute v2 replay without its coral rows | CC BY 4.0 | no |

The root files: this README; `LICENSE` (MIT) and `LICENSE-DATA` (CC BY 4.0); `THIRD_PARTY_NOTICES.md`;
`CITATION.cff` and `.zenodo.json` (the citation, and the code record's metadata for the GitHub release);
`VERSIONS.md`; `HASH_REGISTER.md`; `KEPT_OUT.md`; `REBUILD.md`; `CHANGES_FOR_ARCHIVE.md`, which lists every archived
file that differs from its source, with both SHA-256 values; `SHA256SUMS.txt`, the SHA-256 of every file;
`VERIFY_HASHES.py`; and `.gitattributes`, which tells Git to keep every file's bytes as they are, with no
line-ending conversion, so that the recorded hashes also hold in a Git checkout.

## Versions and hashes

`VERSIONS.md` gives every code version's archive folder, full hash, the recipe that forms the hash and how the
version is rebuilt. `HASH_REGISTER.md` gives, for every hash of Table S4.14 in the paper's Supplement S4, where it
can be checked in this archive; three of them belong to coral bleaching per-visit files that are kept out. To
recompute the code hashes and the file hashes that the archive holds, run, with Python 3.9 and its standard library
only:

```
py -3.9 VERIFY_HASHES.py
```

It writes nothing. To form the five engine constants hashes it imports `treeroute.engine_constants` from each
locked engine version's folder, each time in a separate Python process that writes no bytecode (`-I -B`).
Run it on the unzipped data record, which holds every file. In a clone of the GitHub repository, which holds only
the code and the key text records, the code checks pass, but the file checks of the run records that only the data
record holds report FAIL with "missing" (77 checks); `SHA256SUMS.txt` also lists those files.

## Running the code

The runs used Python 3.9.13 with the 15 fingerprinted libraries of `environment/requirements_py39_core.txt`
(scikit-learn 1.6.1 patched by scikit-learn-intelex 2025.10.0 with oneDAL 2025.10.0, numpy 2.0.2 and the others
there) at four pinned threads, on one laptop under Microsoft Windows 10 Pro, version 22H2. Byte-level reproduction
needs these versions; each run's manifest records them. The figure scripts use Python 3.12 with the libraries of
`environment/requirements_py312_figures.txt` (Python 3.12.10).

The archive alone does not re-run the routing. It holds no per-location values of the tree inputs: they stay with
their providers, and the archived scripts fetch or rebuild them where their sources are recorded, while some cannot
be rebuilt. And it holds none of the engine's fitted trees (specialist trees, correctors and error-weight forests).
`REBUILD.md` gives the rebuild scripts, the order of the coral bleaching chain, the two rebuild inputs that no
archived script writes, how to re-draw the figures and the limits of a rebuild.

## What is not included

Files whose licence is unclear are kept out: the coral bleaching per-visit answers, ours and the rivals', which are
built on CoralTemp; the per-location VT0007 answers and maps, tied to GADM boundaries; the rival input exports that
hold per-location values derived from CoralTemp or TerraClimate; the per-visit cyclone columns and the other coral
tables built on CoralTemp; and a few other files, among them the BARDL rival's fitted maps. Pickles, NumPy and
compressed files and two test reports that hold a host name are left out too, as are the raw third-party layers.
`KEPT_OUT.md` lists every kept-out group, why, and how it is rebuilt where its sources are recorded.

## Licences

The code is under the MIT licence (`LICENSE`; `engine/LICENSE` is the same text). The archive's own data files
(predictions, tables and run records) are under CC BY 4.0 (`LICENSE-DATA`, which names the folders). The
third-party values inside them (the labels, the PM2.5 published rivals' MERRA-2 values, the sample events of the
Global Coral Bleaching Database and the per-region tree-cover statistics of the forest-loss census) keep their
providers' terms: `THIRD_PARTY_NOTICES.md` gives them, with the notices for the works made with SPEIbase, Copernicus
and GSHHG data. The archive includes no third-party code, and the libraries are not redistributed.

## Known documentation issues

The engine's version label '0.0.1-skeleton', which every run manifest records, and its out-of-date
`engine/README.md` stay unchanged: the label sits inside the hash-checked engine code, and the paper cites facts
from the README. The engine's tests are the project's own: 33 of them failed in the recorded full run on 930d961c,
one test file was brought up to date after that run, and the archive's text changes to the tests touch only
docstrings and one comment. Two notes added for the archive describe all this: `engine/README_ARCHIVE.md` (the
engine as it is) and `engine/tests/STALE_TESTS.md` (the 33 tests). No hash-checked engine file is changed.

## Paths

The run records keep the run machine's file paths, an old Windows profile path among them, so that every recorded
fingerprint stays valid. In the files that no hash pins (code, tests, notes, logs, results and two table-build
manifests), the archive copy replaces the user name by `<user>`; folder names built from the profile path, and some
other identifiers, are replaced in the same way by other placeholders in angle brackets.
`CHANGES_FOR_ARCHIVE.md` lists each such file with its SHA-256 before and after.
In unpinned record files, and in the comments and strings of some unpinned scripts, tests and tool outputs, the
author's answers that were quoted word for word are replaced by plain descriptions of the answers;
`CHANGES_FOR_ARCHIVE.md` lists these files with both SHA-256 values.

Inside each folder the project's own relative paths are kept. The paper's supplements cite archive paths; the
frozen fact sheet and the archived records cite project paths, which map as follows (paths without a drive letter
are relative to the project folder, as in the fact sheet; where two rows match, the longer project path applies):

| Project path | Archive path |
|---|---|
| `engine/` | `engine/` |
| `engine/_moved_coral_20261020_014111/`, `engine/_moved_coral_20261020_064437/` | `versions/engine/_moved_coral_20261020_014111/`, `versions/engine/_moved_coral_20261020_064437/` |
| `paper/PAPER_FACTS.md` | `records/fact_sheet/PAPER_FACTS.md` |
| `paper/figures/` | `analysis/paper/figures/` (the folder `fig1/` holds Figure 2, `fig2/` Figure 3, and so on; `FIGURE_NUMBERS.md` records the numbering) |
| `paper/supp_build/s3_13/` | `analysis/paper/supp_build/s3_13/` |
| `paper/checks/` | `records/paper_checks/` |
| `paper/draft/`, `paper/PAPER_OUTLINE.md` and the other folders of `paper/` | not archived: the paper's draft and submission texts and their build folders |
| the project folder's top-level scripts and `all133_regions.txt` | `rebuild/` |
| `presplit_cc/` (the scripts that `REBUILD.md` lists) | `rebuild/presplit_cc/` |
| `_setup_new_pc/` (the three requirement files and `check_env.py`) | `environment/` |
| `APP_PLAN.md`, `PAPER_REFERENCE.md`, `CORAL_DATA_PLAN.md`, `CORAL_LABEL_AUDIT.md`, `DEFORESTATION_SCOPE.md`, `HEADLINE_QUESTIONS_AND_FIXES.md`, `QUESTIONS_ROUND3_HANDOFF.md` | `records/project_docs/` |
| `PM25_RIVALS_PLAN.md`, `NDVI_BASELINE_REPORT.md`, `CRW_BENCHMARK_REPORT.md`, `pm25_rivals.py`, `ndvi_kraft.py`, `defo_papers.py`, `coral_crw.py`, `CORAL_FORECAST.log` | `records/earlier_runs/` |
| `D:/run89full/` (`kraft_even.log`, `kraft/train_cells.csv`, `ndvi_split.txt`, `forest_census.csv`), `D:/pm25_rivals/full/` (`board.csv`, `rivals.log`), `D:/defo_papers/_papers.log` | `records/earlier_runs/` (each file by its name) |
| `D:/coral/target/events_dated.parquet` | `rebuild/inputs/coral/events_dated.parquet` |
| `D:/treeroute/runs/` | `runs/` |
| `D:/treeroute/registry/freeze/` | `records/registry/freeze/` |
| `D:/treeroute/registry/rivals/` | `records/registry/rivals/` |
| `D:/treeroute/registry/` (`inputs.json`, `shipped.json`, `protected_roots.txt`) | `records/registry/` |
| `D:/treeroute/ckpt_20261013/refreeze/old_check_reports/` | `records/registry/superseded_check_reports/ckpt_20261013/refreeze/old_check_reports/` |
| `D:/treeroute/_moved_install_20261015/check_reports_before_refreeze/` | `records/registry/superseded_check_reports/_moved_install_20261015/check_reports_before_refreeze/` |
| `D:/treeroute/rivals/` | `rival_boards/rivals/` |
| `D:/treeroute/rivals_human/` | `rival_boards/rivals_human/` |
| `D:/treeroute/human_index/` | `rival_boards/human_index/` |
| `D:/treeroute/rivals_table/` | `rival_boards/rivals_table/` |
| `D:/treeroute/human_products/` (two product manifests) | `rival_boards/human_products/` |
| `D:/treeroute/rivals_build/_moved/coral_board_pre_fix599_20261021_160319/` | `rival_boards/rivals_build/_moved/coral_board_pre_fix599_20261021_160319/` |
| `D:/treeroute/rivals_build/_moved/20261021_160025_preUnseenFix/`, `.../20261022_070259_preLegalFix/` (`harness.py`) | `versions/rivals_build/_moved/20261021_160025_preUnseenFix/`, `versions/rivals_build/_moved/20261022_070259_preLegalFix/` |
| `D:/treeroute/rivals_build/` (`rivals/`, `evidence/` and the top-level files) | `rivals_code/rivals_build/` |
| `D:/treeroute/human_rivals_build/_moved/` | `versions/human_rivals_build/_moved/` |
| `D:/treeroute/human_rivals_build/` (`human/`, `review_tests/`, the top-level files and four files of `pt/`) | `rivals_code/human_rivals_build/` |
| `D:/treeroute/human_tools/` | `rivals_code/human_tools/` |
| `D:/treeroute/rivals_plan_human/` | `rivals_code/rivals_plan_human/` |
| `D:/treeroute/coral_build/noop/` | `evidence/coral_build/noop/` |
| `D:/treeroute/coral_build/` | `coral_build/` |
| `D:/treeroute/analysis/` | `analysis/` |
| `D:/treeroute/ckpt_20261013/engine_before/treeroute/`, `D:/treeroute/install_20261015/engine_old/treeroute/`, `D:/treeroute/s_20261016/engine_old/treeroute/` | `versions/ckpt_20261013/engine_before/treeroute/`, `versions/install_20261015/engine_old/treeroute/`, `versions/s_20261016/engine_old/treeroute/` |
| `D:/treeroute/engine_v2/engine/`, `D:/treeroute/engine_v2/_moved/`, `D:/treeroute/engine_v2/ALARM_REPORT.txt`, `SPEC_ALARM.txt` | `versions/engine_v2/engine/`, `versions/engine_v2/_moved/`, `versions/engine_v2/ALARM_REPORT.txt`, `versions/engine_v2/SPEC_ALARM.txt` |
| `D:/treeroute/engine_v2/replay_af2_20261021/` | `evidence/engine_v2/replay_af2_20261021/` |
| `D:/treeroute/_moved_nested_treeroute_20261015/` (two report-tooling files) | `versions/_moved_nested_treeroute_20261015/` |
| `D:/treeroute/ckpt_20261013/`, `D:/treeroute/install_20261015/`, `D:/treeroute/s_20261016/` (the no-op checks and smoke runs, and their records) | `evidence/ckpt_20261013/`, `evidence/install_20261015/`, `evidence/s_20261016/` |
| `D:/treeroute/_moved_install_20261015/superseded_ndvi_plan/`, `D:/treeroute/_moved_s_20261016/20261016_580c5b6f/` | `evidence/_moved_install_20261015/superseded_ndvi_plan/`, `evidence/_moved_s_20261016/20261016_580c5b6f/` |
| the other `D:/` folders (the monthly panel, the coral drivers, the download folders of the inputs) | not archived: raw third-party layers and source stores (`KEPT_OUT.md`; `REBUILD.md`) |

Not every file under an archived folder is archived: `KEPT_OUT.md` names the kept-out files by the archive paths
they would have had. A rebuild script reads its inputs at fixed paths such as `D:\coral\target\events_dated.parquet`;
`REBUILD.md` says where to place them.

## How to cite

Please cite the paper and this archive: `CITATION.cff` gives the code record, the data record and the paper
(code record: https://doi.org/10.5281/zenodo.24452866; data record: https://doi.org/10.5281/zenodo.24452794).
