# Hash register

This register gives, for each of the 254 entries of Table S4.14 (the full SHA-256 values printed in the paper's
Supplement S4, grouped as there), where a reader can check it in this archive. Kinds are those of Supplement S4.1:
*file* is the SHA-256 of a file's bytes, and the cell names that file; *engine code* and *stripped code* are the
engine's code hashes; *content* is the SHA-256 of the canonical JSON of a record's content; *recorded* is a value
copied from the named record as the producing tool computed it. For the kinds other than *file*, the cell names the
archived records that hold the value, with the field (or line) where it sits, and the archived files from which it
is recomputed. `VERSIONS.md` gives every code version's folder and recipe, and `VERIFY_HASHES.py` recomputes the
code hashes and the file hashes that the archive holds. The comment-stripped and constants hashes are recomputed
with the engine's own code under Python 3.9.13.

167 of the 170 file hashes are of files in the archive. The other 3 are coral bleaching per-visit answers, which
ruling AT7 keeps out of the public archive (`KEPT_OUT.md`, section A): the two coral row files of the treeroute v2
replay and the coral 2017-2020 row's test predictions. A reader cannot check these three from the archive, and a
rebuild from the public sources may not reproduce them byte for byte (Supplement S4.12). One hash printed in
Supplement S4 has no entry in Table S4.14: f22a6a24, the earlier hash of the compact rival view, which Part 619 printed
only in part (Supplement S4.7.3).

Paths are archive paths. A path ending in `.jsonl` under `rival_boards/rivals/_ledger/` or
`rival_boards/human_index/_ledger/` is a rival ledger, named by the run fingerprint of its run. The written-out
version folders are those of `VERSIONS.md`.

Entries by kind: engine code 6, stripped code 5, content 28, recorded 45, file 170.

### Engine code (S4.3)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 1 | treeroute v1 engine code 7b508557 | engine code | `7b5085572574d767e7ef13a2248ac03af9e5f103f0ef49f5e85e9994d9344dbb` | recorded in `records/registry/freeze/FREEZE_20261006T203115Z.lock.json` (`engine.engine_code_sha256`); `records/registry/freeze/FREEZE_20261007T130812Z.lock.json` (`engine.engine_code_sha256`); `records/registry/freeze/FREEZE_20261007T132431Z.lock.json` (`engine.engine_code_sha256`); recomputed from `versions/ckpt_20261013/engine_before/treeroute/` (`VERSIONS.md`) |
| 2 | comment-stripped engine code of 7b508557 | stripped code | `6d19c3e20e8111b82cb10734c776ce3c2135f653f8896575f86260b1863468b6` | recorded in `records/registry/freeze/FREEZE_20261006T203115Z.lock.json` (`engine.engine_code_hash_comment_stripped`); `records/registry/freeze/FREEZE_20261007T130812Z.lock.json` (`engine.engine_code_hash_comment_stripped`); `records/registry/freeze/FREEZE_20261007T132431Z.lock.json` (`engine.engine_code_hash_comment_stripped`); `runs/pm25/headline/20261007_74e67609/manifest.json` (`engine_code_hash`); recomputed with the engine's own code (Python 3.9.13) |
| 3 | treeroute v1 engine code 1f257395 | engine code | `1f2573957b10b4ddea76bfa38598e35edbc3a593cf2b5eb7b33d1d8e9f386ae1` | recorded in `records/registry/freeze/FREEZE_20261013T102938Z.lock.json` (`engine.engine_code_sha256`); `records/registry/freeze/FREEZE_20261013T103700Z.lock.json` (`engine.engine_code_sha256`); recomputed from `versions/install_20261015/engine_old/treeroute/` (`VERSIONS.md`) |
| 4 | comment-stripped engine code of 1f257395 | stripped code | `810eeca7664fc729a95dad5ea3408899812823c39fb4cb802413cc1fcb62fcaa` | recorded in `records/registry/freeze/FREEZE_20261013T102938Z.lock.json` (`engine.engine_code_hash_comment_stripped`); `records/registry/freeze/FREEZE_20261013T103700Z.lock.json` (`engine.engine_code_hash_comment_stripped`); recomputed with the engine's own code (Python 3.9.13) |
| 5 | treeroute v1 engine code 7a0341ef | engine code | `7a0341eff4e67759bf12542ad5ab0248bf8b2e56d9d2351a30141f67e44f27b8` | recorded in `records/registry/freeze/FREEZE_20261016T012320Z.lock.json` (`engine.engine_code_sha256`); `records/registry/freeze/FREEZE_20261016T012828Z.lock.json` (`engine.engine_code_sha256`); recomputed from `versions/s_20261016/engine_old/treeroute/` (`VERSIONS.md`) |
| 6 | comment-stripped engine code of 7a0341ef | stripped code | `cf566e0549d426ded8adcaa4dbc59f36bc858a755c5cd42726badebd94866024` | recorded in `records/registry/freeze/FREEZE_20261016T012320Z.lock.json` (`engine.engine_code_hash_comment_stripped`); `records/registry/freeze/FREEZE_20261016T012828Z.lock.json` (`engine.engine_code_hash_comment_stripped`); recomputed with the engine's own code (Python 3.9.13) |
| 7 | treeroute v1 engine code 65a177bc | engine code | `65a177bc7cdd47bacca806582bd13be52706ba3da385bb468fe1f0f24b81a0ff` | recorded in `records/registry/freeze/FREEZE_20261016T090651Z.lock.json` (`engine.engine_code_sha256`); `records/registry/freeze/FREEZE_20261016T091126Z.lock.json` (`engine.engine_code_sha256`); `records/registry/freeze/FREEZE_20261017T105545Z.lock.json` (`engine.engine_code_sha256`); recomputed from `versions/engine_65a177bc/treeroute/` (`VERSIONS.md`) |
| 8 | comment-stripped engine code of 65a177bc | stripped code | `13838e41843cf1ec2598a1c3f7383c8ae2371dc094a1f3ec7f63fd7fc073f74a` | recorded in `records/registry/freeze/FREEZE_20261016T090651Z.lock.json` (`engine.engine_code_hash_comment_stripped`); `records/registry/freeze/FREEZE_20261016T091126Z.lock.json` (`engine.engine_code_hash_comment_stripped`); `records/registry/freeze/FREEZE_20261017T105545Z.lock.json` (`engine.engine_code_hash_comment_stripped`); `runs/defo/headline/20261017_d71c61f4/manifest.json` (`engine_code_hash`); `runs/fire/headline/20261017_869d1f38/manifest.json` (`engine_code_hash`); `runs/ndvi/headline/20261016_d1de3158/manifest.json` (`engine_code_hash`); recomputed with the engine's own code (Python 3.9.13) |
| 9 | treeroute v1 engine code 930d961c | engine code | `930d961cdfdd219c36b113174e6c865096f973068e30696850f13d5ec4a60814` | recorded in `records/registry/freeze/FREEZE_20261020T100907Z.lock.json` (`engine.engine_code_sha256`); recomputed from `engine/treeroute/` (`VERSIONS.md`) |
| 10 | comment-stripped engine code of 930d961c | stripped code | `85c64b55c02e638cfcb7cefb0fe92af4870d4faed5c21e3f46bbdcbcd0e3a678` | recorded in `records/registry/freeze/FREEZE_20261020T100907Z.lock.json` (`engine.engine_code_hash_comment_stripped`); `runs/coral/headline/20261020_f3b8e3da/manifest.json` (`engine_code_hash`); recomputed with the engine's own code (Python 3.9.13) |
| 11 | engine constants d1592748 | content | `d1592748460935ec6c2d430357556690d4c69631eff28f028875477ff034207e` | recorded in `records/registry/freeze/FREEZE_20261006T203115Z.lock.json` (`engine_constants.constants_hash`); `records/registry/freeze/FREEZE_20261007T130812Z.lock.json` (`engine_constants.constants_hash`); `records/registry/freeze/FREEZE_20261007T132431Z.lock.json` (`engine_constants.constants_hash`); `runs/pm25/headline/20261007_74e67609/manifest.json` (`engine_constants_hash`); recomputed with the engine's own code (Python 3.9.13) |
| 12 | engine constants 9509bf33 | content | `9509bf337328e5935a352ef2f8b112c9a0174df1ba7940b7fd00c5eeb80cee2d` | recorded in `records/registry/freeze/FREEZE_20261013T102938Z.lock.json` (`engine_constants.constants_hash`); `records/registry/freeze/FREEZE_20261013T103700Z.lock.json` (`engine_constants.constants_hash`); recomputed with the engine's own code (Python 3.9.13) |
| 13 | engine constants 3ef147e5 | content | `3ef147e5959c04166e3dbcd603723259d9c8ed0adab2d34dd4755662fc1e3a5b` | recorded in `records/registry/freeze/FREEZE_20261016T012320Z.lock.json` (`engine_constants.constants_hash`); `records/registry/freeze/FREEZE_20261016T012828Z.lock.json` (`engine_constants.constants_hash`); `records/registry/freeze/FREEZE_20261016T090651Z.lock.json` (`engine_constants.constants_hash`); `records/registry/freeze/FREEZE_20261016T091126Z.lock.json` (`engine_constants.constants_hash`); `records/registry/freeze/FREEZE_20261017T105545Z.lock.json` (`engine_constants.constants_hash`); `records/registry/freeze/FREEZE_20261020T100907Z.lock.json` (`engine_constants.constants_hash`); `runs/coral/headline/20261020_f3b8e3da/manifest.json` (`engine_constants_hash`); `runs/defo/headline/20261017_d71c61f4/manifest.json` (`engine_constants_hash`); `runs/fire/headline/20261017_869d1f38/manifest.json` (`engine_constants_hash`); `runs/ndvi/headline/20261016_d1de3158/manifest.json` (`engine_constants_hash`); recomputed with the engine's own code (Python 3.9.13) |
| 14 | treeroute v1 engine code dd7c0984 (installed, never locked) | engine code | `dd7c0984d3044aac6cf06d7614df7bd7e8622942580a5f1f0bb08c32ed085d38` | recorded in `versions/engine/_moved_coral_20261020_014111/INSTALL_MANIFEST.json` (`build_hash`, `live_hash_after`); `versions/engine/_moved_coral_20261020_064437/INSTALL_MANIFEST.json` (`live_hash_before`); recomputed from `versions/engine_dd7c0984/treeroute/` (`VERSIONS.md`) |
| 15 | common-rival export code | recorded | `b92437095456333c187567fb8db0787baaa0f5ed1a33d6540190e0198cc98f4d` | recorded in `rival_boards/rivals/coral/20261020_f3b8e3da/board.json` (`engine.export_code_sha256`); `rival_boards/rivals/defo/20261017_d71c61f4/board.json` (`engine.export_code_sha256`); `rival_boards/rivals/fire/20261017_869d1f38/board.json` (`engine.export_code_sha256`); `rival_boards/rivals/ndvi/20261016_d1de3158/board.json` (`engine.export_code_sha256`); `rival_boards/rivals/pm25/20261007_74e67609/board.json` (`engine.export_code_sha256`); recomputed from `rivals_code/rivals_build/rivals/export.py` and `layout.py` (`VERSIONS.md`) |
| 16 | treeroute v2, first build (before the review fixes) | recorded | `fc051e5ae25177e0bc1ed6003f7d0869eac4e25761b7262f94941a10ca963f6e` | recorded in `versions/engine_v2/ALARM_REPORT.txt` (line 77); `versions/engine_v2/_moved/pre_skeptic_fixes_20261021/ENGINE_HASH_BEFORE.txt` (line 1); recomputed from `versions/engine_v2_fc051e5a/treeroute/` (`VERSIONS.md`) |
| 17 | treeroute v2, second build (before ruling AF2) | recorded | `663ab8ef0a666edc786339f2b9e4edac9e067751f72f99ed6a229b903a04bbc3` | recorded in `versions/engine_v2/ALARM_REPORT.txt` (line 197, line 78); recomputed from `versions/engine_v2_663ab8ef/treeroute/` (`VERSIONS.md`) |
| 18 | treeroute v2, current build (post hoc replay only; Supplement S5) | recorded | `88f4db2ce7c0a48834243b8e9403a29d8a3dbcc88c00ed44620d9ced79b44b7d` | recorded in `versions/engine_v2/ALARM_REPORT.txt` (line 198); recomputed from `versions/engine_v2/engine/treeroute/` (`VERSIONS.md`) |

### Report code (S4.6, S4.8)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 19 | report tooling (treeroute_report) f3832db1 | recorded | `f3832db1896dac4a6962193ea66fbe37cc2f1ea9be3c7c8d10eca8a4bbc4d049` | recorded in `records/registry/freeze/FREEZE_20261006T203115Z.lock.json` (`report_tooling.sha256`); `records/registry/freeze/FREEZE_20261007T130812Z.lock.json` (`report_tooling.sha256`); `records/registry/freeze/FREEZE_20261007T132431Z.lock.json` (`report_tooling.sha256`); `records/registry/freeze/FREEZE_20261013T102938Z.lock.json` (`report_tooling.sha256`); `records/registry/freeze/FREEZE_20261013T103700Z.lock.json` (`report_tooling.sha256`); `records/registry/freeze/FREEZE_20261016T012320Z.lock.json` (`report_tooling.sha256`); `records/registry/freeze/FREEZE_20261016T012828Z.lock.json` (`report_tooling.sha256`); recomputed from `versions/report_tooling_f3832db1/treeroute_report/` (`VERSIONS.md`) |
| 20 | report tooling (treeroute_report) af64f5f0 | recorded | `af64f5f013ad194fc5aad3bdc7aa99c22ae90941e24e4353105df9f38299d178` | recorded in `records/registry/freeze/FREEZE_20261016T090651Z.lock.json` (`report_tooling.sha256`); `records/registry/freeze/FREEZE_20261016T091126Z.lock.json` (`report_tooling.sha256`); `records/registry/freeze/FREEZE_20261017T105545Z.lock.json` (`report_tooling.sha256`); recomputed from `versions/report_tooling_af64f5f0/treeroute_report/` (`VERSIONS.md`) |
| 21 | report tooling (treeroute_report) 1658e0dd | recorded | `1658e0ddcf7039e6939fb7ad812885297e025682cf15f29d854d5d98da4b3762` | recorded in `records/registry/freeze/FREEZE_20261020T100907Z.lock.json` (`report_tooling.sha256`); recomputed from `engine/treeroute_report/` (`VERSIONS.md`) |
| 22 | coral_report.py | file | `063be40279a1b4ae0937a21eaec73af98fc4fb379349e34cbdb9c67cf2bacf88` | `coral_build/report_scripts/coral_report.py` |
| 23 | make_signed_coral.py (coral package signatures) | file | `ba096e9c31235c0558c4507c53bf01e90ec380df0eb10d37ea2da164e49f6a75` | `coral_build/tools/make_signed_coral.py` |

### Run, PM2.5 (`runs/pm25/headline/20261007_74e67609/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 24 | run fingerprint | content | `74e676096559d7c9fc8bf7d7f62c4909b4c54a16725f80d5b9157bf279808821` | recorded in `runs/pm25/headline/20261007_74e67609/manifest.json` (`fingerprint`); recomputable from the archived configuration and package (not checked for the archive) |
| 25 | dataset-package fingerprint | content | `625f495161572b8ba016661914b48d0fbe467e4cc43747ecbec969ff66a854be` | recorded in `runs/pm25/headline/20261007_74e67609/manifest.json` (`package_fingerprint`) and in the lock `records/registry/freeze/FREEZE_20261006T203115Z.lock.json`; recomputed from the package `engine/datasets/pm25/` |
| 26 | derived settings, content hash (derived_sha256) | content | `5c5bdbbb8dd65384f28374a78ad34afac97637eed29c1db05bce8de5856db5f3` | recorded in `runs/pm25/headline/20261007_74e67609/manifest.json` (`config.derived_sha256`); recomputable from the archived configuration and package (not checked for the archive) |
| 27 | derived.json | file | `3e2d692b74ad64723fb38c8264e2faa5bdfac8e50a224a141f1d5fb19e10cc36` | `runs/pm25/headline/20261007_74e67609/derived.json` |
| 28 | plan.json | file | `4de95c95a3c55c0737efecc3ba959579bf42e49380df81510a2b9912f1c68779` | `runs/pm25/headline/20261007_74e67609/plan.json` |
| 29 | target files | recorded | `ddfe76469a0b2ddc854be68a6856f818e3bad646e7010acdd2c35b5ce7607370` | recorded in `runs/pm25/headline/20261007_74e67609/manifest.json` (`config.target_files_sha256`); the input files it covers are not in the archive |
| 30 | driver files | recorded | `003b34fc785ed5ca8dd2d783e5417cce0c5c5e294cd55d83df3caa0b2a4649cc` | recorded in `runs/pm25/headline/20261007_74e67609/manifest.json` (`config.driver_files_sha256`); the input files it covers are not in the archive |
| 31 | static files | recorded | `3573202dbfaca8839ab11455857005ad6c0922dbe552603e14044c9baf3388dd` | recorded in `runs/pm25/headline/20261007_74e67609/manifest.json` (`config.static_files_sha256`); the static table it covers is archived (`engine/datasets/pm25/data/static/`) |
| 32 | feature list | recorded | `74ecd64676532c10995ebc0ded0bdc2040057b10bfe1ffcb116290b90b6c5d5c` | recorded in `runs/pm25/headline/20261007_74e67609/manifest.json` (`feature_list_hash`) |
| 33 | adoption.json | file | `b6408c90560b458543f0b1d7d46fc7f4c70de110ff2e6e2ad0e8cdef27ec4335` | `runs/pm25/headline/20261007_74e67609/adoption.json` |
| 34 | adoption_lead_12.json | file | `c1987c1e3b1f1f93e379958bafb1a895cbe4b2a61a58ec068356f6ecd520807f` | `runs/pm25/headline/20261007_74e67609/adoption_lead_12.json` |
| 35 | adoption_lead_6.json | file | `7f033ea82f535731fe30940e6aa24b3059562038449b3a75acbff210f39256bf` | `runs/pm25/headline/20261007_74e67609/adoption_lead_6.json` |

### Run, NDVI (`runs/ndvi/headline/20261016_d1de3158/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 36 | run fingerprint | content | `d1de3158cad5ab44a70e5fb6f3cb0956bb268be553e218103c4fb5f58f3bfb8b` | recorded in `runs/ndvi/headline/20261016_d1de3158/manifest.json` (`fingerprint`); recomputable from the archived configuration and package (not checked for the archive) |
| 37 | dataset-package fingerprint | content | `edbc45b52643dcddc8ddb3928b3f955ad1a404e227051532f00734a3e01227bf` | recorded in `runs/ndvi/headline/20261016_d1de3158/manifest.json` (`package_fingerprint`) and in the locks `records/registry/freeze/FREEZE_20261007T132431Z.lock.json`, `records/registry/freeze/FREEZE_20261013T103700Z.lock.json`, `records/registry/freeze/FREEZE_20261016T012320Z.lock.json`, `records/registry/freeze/FREEZE_20261016T090651Z.lock.json`; recomputed from the package `engine/datasets/ndvi/` |
| 38 | derived settings, content hash (derived_sha256) | content | `e2836c5eda7ac7ae280e2cd91e7043beaf8a1a8c0d6517ed7fa6fb82faf86cec` | recorded in `runs/ndvi/headline/20261016_d1de3158/manifest.json` (`config.derived_sha256`); recomputable from the archived configuration and package (not checked for the archive) |
| 39 | derived.json | file | `8ecc92b58cbd5f65867d477472001085646553c891773ab382fd542c470bb950` | `runs/ndvi/headline/20261016_d1de3158/derived.json`; identical copies: `evidence/_moved_s_20261016/20261016_580c5b6f/derived.json`, `evidence/_moved_install_20261015/superseded_ndvi_plan/20261014_4e505c2b/derived.json`, `evidence/ckpt_20261013/superseded_ndvi_plan/20261012_eb4cde0b/derived.json` |
| 40 | plan.json | file | `c63983fb88f7795c93347b27a413b118515718a044313763c7e1da63b4ce6ab6` | `runs/ndvi/headline/20261016_d1de3158/plan.json`; identical copies: `evidence/_moved_s_20261016/20261016_580c5b6f/plan.json`, `evidence/_moved_install_20261015/superseded_ndvi_plan/20261014_4e505c2b/plan.json`, `evidence/ckpt_20261013/superseded_ndvi_plan/20261012_eb4cde0b/plan.json` |
| 41 | target files | recorded | `dad0555d713b1c314649b0424d6d536d706347d78d374937fb174909e8c54d04` | recorded in `runs/ndvi/headline/20261016_d1de3158/manifest.json` (`config.target_files_sha256`); the input files it covers are not in the archive |
| 42 | driver files | recorded | `1e612e17effc0d071b82f39a98c84b87967da09d94b805c8263e7241d4508876` | recorded in `runs/ndvi/headline/20261016_d1de3158/manifest.json` (`config.driver_files_sha256`); the input files it covers are not in the archive |
| 43 | static files | recorded | `7fdfb7af6c86f610c0c21446e092926a06b576cca4527607b7befc967559a27a` | recorded in `runs/ndvi/headline/20261016_d1de3158/manifest.json` (`config.static_files_sha256`); the static table it covers is archived (`engine/datasets/ndvi/data/static/`) |
| 44 | feature list | recorded | `77199f1a353c3fb1b9119ebd30ea624a270c46d186c2c7a0688244a3af0c74a4` | recorded in `runs/ndvi/headline/20261016_d1de3158/manifest.json` (`feature_list_hash`) |
| 45 | adoption.json | file | `d5ae6f1dd672868166425c6b7590ca911596b29a0c9ccf198feb594623963e59` | `runs/ndvi/headline/20261016_d1de3158/adoption.json` |
| 46 | adoption_lead_12.json | file | `e140ea4d28a53229ab4338f497d727767f19b019faae100b817167577a933411` | `runs/ndvi/headline/20261016_d1de3158/adoption_lead_12.json` |
| 47 | adoption_lead_6.json | file | `47b35f1da7d3ddc44f483ad1e524bb5c03841ebdd5f41d4d0eb506c225097d4c` | `runs/ndvi/headline/20261016_d1de3158/adoption_lead_6.json` |

### Run, Burned fraction (`runs/fire/headline/20261017_869d1f38/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 48 | run fingerprint | content | `869d1f38524d4b4c776538c54fe71f22b6d3d30058a81618d574643a6fdf95dd` | recorded in `runs/fire/headline/20261017_869d1f38/manifest.json` (`fingerprint`); recomputable from the archived configuration and package (not checked for the archive) |
| 49 | dataset-package fingerprint | content | `18c7bbb8634cf591fded8306fe5b3c34c372c63f1129cc56c03f747e6b9563f0` | recorded in `runs/fire/headline/20261017_869d1f38/manifest.json` (`package_fingerprint`) and in the locks `records/registry/freeze/FREEZE_20261007T130812Z.lock.json`, `records/registry/freeze/FREEZE_20261013T102938Z.lock.json`, `records/registry/freeze/FREEZE_20261016T012828Z.lock.json`, `records/registry/freeze/FREEZE_20261016T091126Z.lock.json`; recomputed from the package `engine/datasets/fire/` |
| 50 | derived settings, content hash (derived_sha256) | content | `57475923290ae19ce4af48ed70b2fa48aaa9d66b3c380e6f6fffb7d72de2455c` | recorded in `runs/fire/headline/20261017_869d1f38/manifest.json` (`config.derived_sha256`); recomputable from the archived configuration and package (not checked for the archive) |
| 51 | derived.json | file | `9255562ca6959e9ec4036021420d47c0545391eb8713bd176d1c8853003c6942` | `runs/fire/headline/20261017_869d1f38/derived.json` |
| 52 | plan.json | file | `806f3d9bfeed3ccbe17ff7fa3963cd94f836c1de3fda7ec1c3d5abaaf642dfd7` | `runs/fire/headline/20261017_869d1f38/plan.json` |
| 53 | target files | recorded | `8f67233c6628cc8c07d7fa2d8b59b2073af0a1384d566e4a0f5c3dcf1f5a2791` | recorded in `runs/fire/headline/20261017_869d1f38/manifest.json` (`config.target_files_sha256`); the input files it covers are not in the archive |
| 54 | driver files | recorded | `dd147c82d68bc883af37db6cc2aea95d4730ea8394f94ca676a6f8ee5d60840d` | recorded in `runs/fire/headline/20261017_869d1f38/manifest.json` (`config.driver_files_sha256`); the input files it covers are not in the archive |
| 55 | static files | recorded | `30b298a937307ebaf9f21fe863599cd22f6c6e59cafb939fb224e33c909ac0e1` | recorded in `runs/fire/headline/20261017_869d1f38/manifest.json` (`config.static_files_sha256`); the static table it covers is archived (`engine/datasets/fire/data/static/`) |
| 56 | feature list | recorded | `fd41607e2a7f4468762d909e3018c0cdb39f2cb05e9dd2a3c370b6164aea9a68` | recorded in `runs/fire/headline/20261017_869d1f38/manifest.json` (`feature_list_hash`) |
| 57 | adoption.json | file | `75f70e5cd22039b62c65f0e4546f669de484edd21d5a9cec581fc0ed774260ad` | `runs/fire/headline/20261017_869d1f38/adoption.json` |
| 58 | adoption_lead_12.json | file | `baa28a8c8920c20802c0f848acda7b03a8e6b03896e47dcaaf6bdaddf386f52b` | `runs/fire/headline/20261017_869d1f38/adoption_lead_12.json` |
| 59 | adoption_lead_6.json | file | `f36470a1af96577d9013bbc45c28df743ba5094dbbb4db2d4f63e23e5872c576` | `runs/fire/headline/20261017_869d1f38/adoption_lead_6.json` |

### Run, Forest loss (`runs/defo/headline/20261017_d71c61f4/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 60 | run fingerprint | content | `d71c61f4543fa5b2d54c4de3589eb159cf0d3b4d65b54a677d66413c6b90ccf9` | recorded in `runs/defo/headline/20261017_d71c61f4/manifest.json` (`fingerprint`); recomputable from the archived configuration and package (not checked for the archive) |
| 61 | dataset-package fingerprint | content | `d607314e8d571703e3e8dd44d15cb6da4f649e552328b077b38b0db8336f5996` | recorded in `runs/defo/headline/20261017_d71c61f4/manifest.json` (`package_fingerprint`) and in the lock `records/registry/freeze/FREEZE_20261017T105545Z.lock.json`; recomputed from the package `engine/datasets/defo/` |
| 62 | derived settings, content hash (derived_sha256) | content | `25c0f5b4ae025d0b155285f3cfc85d7ddac5a2be36e0c4fce99daf6f1970e68f` | recorded in `runs/defo/headline/20261017_d71c61f4/manifest.json` (`config.derived_sha256`); recomputable from the archived configuration and package (not checked for the archive) |
| 63 | derived.json | file | `e17b92cfe8ba31cc6a91afcf52343fdc2bd57ccefbf5c455bea2ef82f133ab16` | `runs/defo/headline/20261017_d71c61f4/derived.json` |
| 64 | plan.json | file | `6ec38e12d9fb684da3a60cf95f18ddf302b42d1bb2b381b534a9a125860366a3` | `runs/defo/headline/20261017_d71c61f4/plan.json` |
| 65 | target files | recorded | `e4c7cb6809ca743f1f1a0cdb6d740c0e34d2cf536b88b05e25378aa748258993` | recorded in `runs/defo/headline/20261017_d71c61f4/manifest.json` (`config.target_files_sha256`); the input files it covers are not in the archive |
| 66 | driver files | recorded | `61e37766f6011bd244db44bf33547fa6fe02377d5ef550aaf31f5de31fac1da1` | recorded in `runs/defo/headline/20261017_d71c61f4/manifest.json` (`config.driver_files_sha256`); the input files it covers are not in the archive |
| 67 | static files | recorded | `b7aa9016a63437a168c1c2ec50b915f8b8f7ca983168139336783a8c954e4937` | recorded in `runs/defo/headline/20261017_d71c61f4/manifest.json` (`config.static_files_sha256`); the input files it covers are not in the archive |
| 68 | feature list | recorded | `48f26c461df1c4895b40e37ccc579c703968e25800964d2a052c35384d1fdf00` | recorded in `runs/defo/headline/20261017_d71c61f4/manifest.json` (`feature_list_hash`) |
| 69 | adoption.json | file | `d8ebdd4cc458b276938bee2bf165088ac9c622f133518031f7c6c806592ee54a` | `runs/defo/headline/20261017_d71c61f4/adoption.json` |
| 70 | adoption_lead_1.json | file | `0e3c1116ebf4d4c47d9dd1ab68bda512db152f105b41dcaf04d2890592486c7b` | `runs/defo/headline/20261017_d71c61f4/adoption_lead_1.json` |

### Run, Coral bleaching (`runs/coral/headline/20261020_f3b8e3da/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 71 | run fingerprint | content | `f3b8e3daee7474db63e1d10d15b4b93d7044e35408efb31e7611958633e7f362` | recorded in `runs/coral/headline/20261020_f3b8e3da/manifest.json` (`fingerprint`); recomputable from the archived configuration and package (not checked for the archive) |
| 72 | dataset-package fingerprint | content | `5b9383f0446df0f12e460cccb2bcd2e58d09fbf22b234cf2943a07aac14644c9` | recorded in `runs/coral/headline/20261020_f3b8e3da/manifest.json` (`package_fingerprint`) and in the lock `records/registry/freeze/FREEZE_20261020T100907Z.lock.json`; recomputed from the package `engine/datasets/coral/` |
| 73 | derived settings, content hash (derived_sha256) | content | `0afecb5ec4b1c4cf3985026ae54e13da245d6be260b1e2dd834a731d8d96f8f9` | recorded in `runs/coral/headline/20261020_f3b8e3da/manifest.json` (`config.derived_sha256`); recomputable from the archived configuration and package (not checked for the archive) |
| 74 | derived.json | file | `5fd02863f8b91573cf145edc98db7f8b4a9d6a9fd34a1519ef0a0f831e184660` | `runs/coral/headline/20261020_f3b8e3da/derived.json` |
| 75 | plan.json | file | `89bd87359d08d02a00faffb91eae0bba02f46704791c35ea3a867b8b7ce39ca7` | `runs/coral/headline/20261020_f3b8e3da/plan.json` |
| 76 | target files | recorded | `e1239c53e1a8b2225cd06a5b5f4240e809a299ccff86fba730b3fdd53b8abad6` | recorded in `runs/coral/headline/20261020_f3b8e3da/manifest.json` (`config.target_files_sha256`); the input files it covers are not in the archive |
| 77 | driver files | recorded | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` | recorded in `runs/coral/headline/20261020_f3b8e3da/manifest.json` (`config.driver_files_sha256`); the input files it covers are not in the archive |
| 78 | static files | recorded | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` | recorded in `runs/coral/headline/20261020_f3b8e3da/manifest.json` (`config.static_files_sha256`); the input files it covers are not in the archive |
| 79 | feature list | recorded | `90950e1c40e69fe4b3800f90d141eaaaab476fbcc77a2488a9fe2fec878001ad` | recorded in `runs/coral/headline/20261020_f3b8e3da/manifest.json` (`feature_list_hash`) |
| 80 | adoption.json | file | `2106a36efee4f9fc0650ed7c821a6f8f73c3fdd10c21674f7c8a24b27d80da2f` | `runs/coral/headline/20261020_f3b8e3da/adoption.json` |
| 81 | adoption_lead_183.json | file | `0f2d240c37f8e293b40ff3b49048ab0b4345f22ae14edcd9c80df05147eff1fb` | `runs/coral/headline/20261020_f3b8e3da/adoption_lead_183.json` |
| 82 | adoption_lead_365.json | file | `3708ac30db065b8f4ed92ec2266dbe44ffb7141e8c25447da92bd6e8a6a654bf` | `runs/coral/headline/20261020_f3b8e3da/adoption_lead_365.json` |

### Lock FREEZE_20261006T203115Z, PM2.5 (`records/registry/freeze/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 83 | lock file | file | `cb41d40c500aa13cea87f8c117598a58f0162fc4e9933c8e2bf919f519f05c9b` | `records/registry/freeze/FREEZE_20261006T203115Z.lock.json` |
| 84 | protocol document | file | `d1d6abaadf200bd2e8b76ce5ffeba2818d15816325d4648bfea811ee4a87a12d` | `records/registry/freeze/PREREGISTRATION_20261006T203115Z.md` |
| 85 | deep check report | recorded | `cff2356c26373716d89ede081eaf743f2401d7fba719c6214ed77bec748ba278` | recorded in `records/registry/freeze/FREEZE_20261006T203115Z.lock.json` (`packages[0].check_report.sha256`); the report itself: `runs/pm25/check/check_deep_625f49516157.json` |

### Lock FREEZE_20261007T130812Z, burned fraction (`records/registry/freeze/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 86 | lock file | file | `d77da0b854f86e0c96b3e2a994d942f2d5199cd8cdaba5d9c9ec55df0d368d66` | `records/registry/freeze/FREEZE_20261007T130812Z.lock.json` |
| 87 | protocol document | file | `347d031107b1ab0bb1d972d705f96f5ae5a9ac12a4586872cb389db48a904197` | `records/registry/freeze/PREREGISTRATION_20261007T130812Z.md` |
| 88 | deep check report | recorded | `d5cda829093909d35799046e8ceb5cd8c6eac74b966c84252e8e4ed25ca335fd` | recorded in `records/registry/freeze/FREEZE_20261007T130812Z.lock.json` (`packages[0].check_report.sha256`); the report itself: `records/registry/superseded_check_reports/ckpt_20261013/refreeze/old_check_reports/fire/check_deep_18c7bbb8634c.json` |

### Lock FREEZE_20261007T132431Z, NDVI (`records/registry/freeze/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 89 | lock file | file | `7b34725519b5d9332f094ede777a35f000b5427af130b256871ad250d73a0744` | `records/registry/freeze/FREEZE_20261007T132431Z.lock.json` |
| 90 | protocol document | file | `8c3003344d350b71ce0b84aeecc2aa1979e827a5be2b14d35ad032cfbff46866` | `records/registry/freeze/PREREGISTRATION_20261007T132431Z.md` |
| 91 | deep check report | recorded | `79cd9c58438e36f85583c72eaf74f89f108b453355fa7ca3c39bc70e146573f7` | recorded in `records/registry/freeze/FREEZE_20261007T132431Z.lock.json` (`packages[0].check_report.sha256`); the report itself: `records/registry/superseded_check_reports/ckpt_20261013/refreeze/old_check_reports/ndvi/check_deep_edbc45b52643.json` |

### Lock FREEZE_20261013T102938Z, burned fraction (`records/registry/freeze/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 92 | lock file | file | `204040c8f1194131c1903c17abd855521f4db122053a59a3c2975ebe24cd5d93` | `records/registry/freeze/FREEZE_20261013T102938Z.lock.json` |
| 93 | protocol document | file | `1654e538625da509e641dd69bf0bf098e64a98a7e18f6506cce03e4e7abf22b9` | `records/registry/freeze/PREREGISTRATION_20261013T102938Z.md` |
| 94 | deep check report | recorded | `dd66fcb76f49319de2ac666bc810f40e953dda9d6e5507a42bb6ff7e79f1b9ce` | recorded in `records/registry/freeze/FREEZE_20261013T102938Z.lock.json` (`packages[0].check_report.sha256`); the report itself: `records/registry/superseded_check_reports/_moved_install_20261015/check_reports_before_refreeze/fire/check_deep_18c7bbb8634c.json` |

### Lock FREEZE_20261013T103700Z, NDVI (`records/registry/freeze/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 95 | lock file | file | `4b4606e59443e24123c05694fa186d36ec0b4e790a03f89cc33c70ff607289d9` | `records/registry/freeze/FREEZE_20261013T103700Z.lock.json` |
| 96 | protocol document | file | `9bd51d5529b4459f3432611c94a97ec0a9a4c94b371c1c1932013cdeac55ae09` | `records/registry/freeze/PREREGISTRATION_20261013T103700Z.md` |
| 97 | deep check report | recorded | `72019d67d962fdfa6abac20d9b40588d2a20d87a87fc0cc4f8bd439aa34e89e9` | recorded in `records/registry/freeze/FREEZE_20261013T103700Z.lock.json` (`packages[0].check_report.sha256`); the report itself: `records/registry/superseded_check_reports/_moved_install_20261015/check_reports_before_refreeze/ndvi/check_deep_edbc45b52643.json` |

### Lock FREEZE_20261016T012320Z, NDVI (`records/registry/freeze/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 98 | lock file | file | `b2da313aa4ccef5b42d8156d4f72432387de87bfec04b1f882ca81754259134b` | `records/registry/freeze/FREEZE_20261016T012320Z.lock.json` |
| 99 | protocol document | file | `f41a0fbda9f402c437f2b794375963f4a414eb64b9b358ab289ef639912bc4c4` | `records/registry/freeze/PREREGISTRATION_20261016T012320Z.md` |
| 100 | deep check report | recorded | `dabcb2c4d0b56808ada45da950a22e7d69f73b85a13ea7580f5513952a063eff` | recorded in `records/registry/freeze/FREEZE_20261016T012320Z.lock.json` (`packages[0].check_report.sha256`); the report itself was not found, so only the lock holds this value |

### Lock FREEZE_20261016T012828Z, burned fraction (`records/registry/freeze/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 101 | lock file | file | `184e9c7c55525cfc5028dc459ddc8083fa604deba53133e4fc639b9980590b3a` | `records/registry/freeze/FREEZE_20261016T012828Z.lock.json` |
| 102 | protocol document | file | `4ebf028ceeddfb9bd1197d6691b3fc1c6676df8e6e1a273433b8b39ed332711f` | `records/registry/freeze/PREREGISTRATION_20261016T012828Z.md` |
| 103 | deep check report | recorded | `b6f87ffb42afc2e62151bf46ed906b89ab5f61f20ac87ed771df6d8f2a6a318b` | recorded in `records/registry/freeze/FREEZE_20261016T012828Z.lock.json` (`packages[0].check_report.sha256`); the report itself was not found, so only the lock holds this value |

### Lock FREEZE_20261016T090651Z, NDVI (`records/registry/freeze/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 104 | lock file | file | `960bc7d51829d93bc72bf4b0055fff44500f1208543c4157c81ccce869fbab99` | `records/registry/freeze/FREEZE_20261016T090651Z.lock.json` |
| 105 | protocol document | file | `1b757ac7745e14da6b78a0919d70ee10c654b855ec33bc457aa53d94752d0bb7` | `records/registry/freeze/PREREGISTRATION_20261016T090651Z.md` |
| 106 | deep check report | recorded | `4b2a2b9b4ab75b3e7692bd0d2ace1f56731e6994e9dd455fc254497dff634ffd` | recorded in `records/registry/freeze/FREEZE_20261016T090651Z.lock.json` (`packages[0].check_report.sha256`); the report itself: `runs/ndvi/check/check_deep_edbc45b52643.json` |

### Lock FREEZE_20261016T091126Z, burned fraction (`records/registry/freeze/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 107 | lock file | file | `f8c297e5ff761c901c54efccfb25530d67dd37d623737b0954e2492d49470aa7` | `records/registry/freeze/FREEZE_20261016T091126Z.lock.json` |
| 108 | protocol document | file | `89d97c8020f7cddac397cc6b5d7f238e60ef5509ab1adcb9b8bb8aa84e24db8e` | `records/registry/freeze/PREREGISTRATION_20261016T091126Z.md` |
| 109 | deep check report | recorded | `4f1e1bc1ea2e24634573c1d548494427a031d859f6806bb9f941eb2be904b48f` | recorded in `records/registry/freeze/FREEZE_20261016T091126Z.lock.json` (`packages[0].check_report.sha256`); the report itself: `runs/fire/check/check_deep_18c7bbb8634c.json` |

### Lock FREEZE_20261017T105545Z, forest loss (`records/registry/freeze/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 110 | lock file | file | `a59408bb2f40a8987b3cc407930ab6d944dc3fe2a92c32cb19c3a9766d26e0e9` | `records/registry/freeze/FREEZE_20261017T105545Z.lock.json` |
| 111 | protocol document | file | `20e879c198257e5a03f8697eabc18db4bcc77c704760f09a1b90658654c2df92` | `records/registry/freeze/PREREGISTRATION_20261017T105545Z.md` |
| 112 | deep check report | recorded | `c19d60c0885a8c7c8992aa0a88999e7163c512409cbe27d4518ec63f7e91730d` | recorded in `records/registry/freeze/FREEZE_20261017T105545Z.lock.json` (`packages[0].check_report.sha256`); the report itself: `runs/defo/check/check_deep_d607314e8d57.json` |

### Lock FREEZE_20261020T100907Z, coral bleaching (`records/registry/freeze/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 113 | lock file | file | `70b163cd8ac671f554cb18101f433c64e7d047f40226434320bc45a1f5620567` | `records/registry/freeze/FREEZE_20261020T100907Z.lock.json` |
| 114 | protocol document | file | `2b644584910b55cd785f0d6f52d11bd5df9a8899de1f66e4e54a57599fd740f4` | `records/registry/freeze/PREREGISTRATION_20261020T100907Z.md` |
| 115 | deep check report | recorded | `45baa163b824ca5b87b969c9692b209266a60a8a5693284f2d41b9d756fc4e7e` | recorded in `records/registry/freeze/FREEZE_20261020T100907Z.lock.json` (`packages[0].check_report.sha256`); the report itself: `runs/coral/check/check_deep_5b9383f0446d.json` |

### Signature records (S4.9; `records/registry/freeze/` and `records/registry/rivals/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 116 | coral protocol document signature record | file | `611db73093e719179e06c877c9d7d9aecca0e76f1a6340873366ae5233822e0b` | `records/registry/freeze/PREREGISTRATION_20261020T100907Z.SIGNED.md` |
| 117 | common-rival protocol signature record | file | `5bf9e92b3de6ef74262e270aaa169fabc1ad4b5fcde0f52b4c6f4cca27c88a3b` | `records/registry/rivals/PREREGISTRATION_rivals_common_20261021T125123Z.SIGNED.md` |
| 118 | Part A signature record | file | `a4d663dae47212c24d634208273e8ad0395b8182c1b6fb26214cd80c27f4cb28` | `records/registry/rivals/PREREGISTRATION_human_partA_20261025T105940Z.SIGNED.txt` |

### Common-rival harness and protocol (S4.7.1)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 119 | harness 46d0306a (signed) | recorded | `46d0306af3b67f15edf36d8c1fd6ac5e47a1fac06bdf33548b9c88f4decc9485` | recorded in `rival_boards/rivals_build/_moved/coral_board_pre_fix599_20261021_160319/20261020_f3b8e3da/board.json` (`harness_code_sha256`); recomputed from `versions/harness_46d0306a/rivals/` (`VERSIONS.md`) |
| 120 | harness 71457aa9 | recorded | `71457aa902d30dde17a4a88e8d5c7f1de85515c70d2d7ac4745967066f243b97` | recorded in `rival_boards/rivals/coral/20261020_f3b8e3da/board.json` (`harness_code_sha256`); `rival_boards/rivals/fire/20261017_869d1f38/board.json` (`harness_code_sha256`); recomputed from `versions/harness_71457aa9/rivals/` (`VERSIONS.md`) |
| 121 | harness b6ea97b7 | recorded | `b6ea97b72b5a8f79f7f8257f1e4afd00d7783479fada03eea9101410fa509bf2` | recorded in `rival_boards/rivals/defo/20261017_d71c61f4/board.json` (`harness_code_sha256`); `rival_boards/rivals/ndvi/20261016_d1de3158/board.json` (`harness_code_sha256`); `rival_boards/rivals/pm25/20261007_74e67609/board.json` (`harness_code_sha256`); recomputed from `rivals_code/rivals_build/rivals/` (`VERSIONS.md`) |
| 122 | signed common-rival protocol document | file | `91c62b07dbc9505dcc3b7391cef3722ece97c29b6140de7e73e8b1b83dd95bb5` | `records/registry/rivals/PREREGISTRATION_rivals_common_20261021T125123Z.md`; identical copies: `rivals_code/rivals_build/PREREGISTRATION_DRAFT_rivals_common.md` |

### Common-rival board, Coral bleaching (`rival_boards/rivals/coral/20261020_f3b8e3da/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 123 | board.json | file | `61a2482d0133a1aa3a01d8eab6f8e0a1a3d0c10c6cdc485d2731abb06fb931ec` | `rival_boards/rivals/coral/20261020_f3b8e3da/board.json` |
| 124 | picks content | content | `5ad9502f975c771ecbc7406d98a57eaba5b308d3920fbd5d77f8269e2567639b` | recorded in `rival_boards/rivals/_ledger/f3b8e3daee7474db63e1d10d15b4b93d7044e35408efb31e7611958633e7f362.jsonl` (`picks_content_sha256`); the content of the board's picks file, which is archived |
| 125 | picks.json | file | `e152553533151f172671b2f4c59ef4ee2bbe1ff4dde625a239d22c477f12a6f8` | `rival_boards/rivals/coral/20261020_f3b8e3da/picks.json` |
| 126 | picks.json of the first rival board (46d0306a; moved aside) | file | `8492c4f2377f917542e431dd7f253f20f4c488f567f9486f213978a7bec5d0b5` | `rival_boards/rivals_build/_moved/coral_board_pre_fix599_20261021_160319/20261020_f3b8e3da/picks.json` |

### Common-rival board, Burned fraction (`rival_boards/rivals/fire/20261017_869d1f38/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 127 | board.json | file | `b9f59f9e397a0009404fe161773d801e809b910a95c3812b852e33cab9cd958b` | `rival_boards/rivals/fire/20261017_869d1f38/board.json` |
| 128 | picks content | content | `84fa943200d5d91e45b9120909d506d4fa1b1fb6983e5b6a09b1935e56c486c5` | recorded in `rival_boards/rivals/_ledger/869d1f38524d4b4c776538c54fe71f22b6d3d30058a81618d574643a6fdf95dd.jsonl` (`picks_content_sha256`); the content of the board's picks file, which is archived |
| 129 | picks.json | file | `33f9e968ea7c01dc8e764d89cfa8fd801fbb721395ecdc577c9e722dbabac207` | `rival_boards/rivals/fire/20261017_869d1f38/picks.json` |

### Common-rival board, PM2.5 (`rival_boards/rivals/pm25/20261007_74e67609/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 130 | board.json | file | `b2bcf4152f91c7ab2968f435d59fb9154d650431c2f83a874c0034cb59e01be0` | `rival_boards/rivals/pm25/20261007_74e67609/board.json` |
| 131 | picks content | content | `714f7e2e4e7dce0801febf81f7324d8654532297f806df7383c5b3adff0a3a6c` | recorded in `rival_boards/rivals/_ledger/74e676096559d7c9fc8bf7d7f62c4909b4c54a16725f80d5b9157bf279808821.jsonl` (`picks_content_sha256`); the content of the board's picks file, which is archived |
| 132 | picks.json | file | `4b567830a4ace95e2b5b5e11128ac6fe374a897364fccc67037b853db3fb27fc` | `rival_boards/rivals/pm25/20261007_74e67609/picks.json` |

### Common-rival board, Forest loss (`rival_boards/rivals/defo/20261017_d71c61f4/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 133 | board.json | file | `440e86a78d1ec69d17b2bbd119ddce8490769d689601ad7ffc1f3719922a4f6d` | `rival_boards/rivals/defo/20261017_d71c61f4/board.json` |
| 134 | picks content | content | `e80630658ac348551af5154eb829d720517e3bc8b18e51694c7a848697102567` | recorded in `rival_boards/rivals/_ledger/d71c61f4543fa5b2d54c4de3589eb159cf0d3b4d65b54a677d66413c6b90ccf9.jsonl` (`picks_content_sha256`); the content of the board's picks file, which is archived |
| 135 | picks.json | file | `08b1678703fcf30bfdcaeec003010a97a5311c1813c9e6e3282325f77e44cc5c` | `rival_boards/rivals/defo/20261017_d71c61f4/picks.json` |

### Common-rival board, NDVI (`rival_boards/rivals/ndvi/20261016_d1de3158/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 136 | board.json | file | `f19d11444254b7d0afdff9df6fca4ca710de14a3c11b78dbcd609f451cbe4b87` | `rival_boards/rivals/ndvi/20261016_d1de3158/board.json` |
| 137 | picks content | content | `007a474f01823826852861c60363ff276c77ecf09d46c10cb908052ae680fefd` | recorded in `rival_boards/rivals/_ledger/d1de3158cad5ab44a70e5fb6f3cb0956bb268be553e218103c4fb5f58f3bfb8b.jsonl` (`picks_content_sha256`); the content of the board's picks file, which is archived |
| 138 | picks.json | file | `852aa1bfbf3ca3085f4700cc55e2bbd76bd5d6abae8e015ca0ea2fd5512ffbd6` | `rival_boards/rivals/ndvi/20261016_d1de3158/picks.json` |

### Published-rival tool, registries and protocol (S4.7.2; registries in `rivals_code/human_rivals_build/human/registry/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 139 | tool 32ec5df0 | recorded | `32ec5df06e8022be17393cbd1e6fa2e0929876a1f9835a8b8e707761a13133a5` | recorded in `rival_boards/rivals_human/_moved/20261025_ndvi_board_pre_part618/human_board.json` (`tool_code_sha256`); `rival_boards/rivals_human/coral/20261020_f3b8e3da/human_board.json` (`tool_code_sha256`); `rival_boards/rivals_human/defo/20261017_d71c61f4/human_board.json` (`tool_code_sha256`); `rival_boards/rivals_human/pm25/20261007_74e67609/human_board.json` (`tool_code_sha256`); recomputed from `versions/rival_tool_32ec5df0/` (`VERSIONS.md`) |
| 140 | registry schema (_schema.yaml) a3cda623 | file | `a3cda6238677d3f13fd4a324e43dfc4b982a26d999f80baf200b9f4e49a33c61` | `rivals_code/human_rivals_build/pt/ag/full1/grid_ok0/_registry_dry/_schema.yaml` |
| 141 | product registry (_products.yaml) 4e479759 | file | `4e4797597c0a7c76815159d7ce5fa3cf723d2b996d1e3b67a05968136bcb5d1f` | `versions/human_rivals_build/_moved/20261025T194657Z_partB_baseline/registry/_products.yaml`; identical copies: `versions/human_rivals_build/_moved/20261022_review_fixes_before/registry___products.yaml` |
| 142 | tool cd956f1d | recorded | `cd956f1dbd0f9b0f2ada37c1a27f8212768d94fc6242cab0686bf7c71608a273` | recorded in `rival_boards/rivals_human/ndvi/20261016_d1de3158/human_board.json` (`tool_code_sha256`); recomputed from `versions/rival_tool_cd956f1d/` (`VERSIONS.md`) |
| 143 | registry schema (_schema.yaml) 0d4dbcb7 | file | `0d4dbcb7d81e32b901c35395df3fc4f78619493a9d18bb52711f3c6daf7b8ced` | `rivals_code/human_rivals_build/human/registry/_schema.yaml` |
| 144 | NDVI registry file at the Part A signature (ndvi.yaml) | file | `e24195f1a89454abbeb3aa0a406372849aad28c53d90bb80eb0255b2327d1d58` | `versions/rival_tool_registry_part_a/ndvi.yaml` (a backup copy, Supplement S4.7.2, file a6668f3b53ecbce0@v2, archived under this name) |
| 145 | signed published-rival protocol document (Part A) | file | `4db899658f22e30d50e12980b4db66e947b9cdb519fab8b52817968e477360b8` | `records/registry/rivals/PREREGISTRATION_human_partA_20261025T105940Z.txt`; identical copies: `rivals_code/human_rivals_build/PREREGISTRATION_DRAFT_human_partA.txt` |

### Published-rival board, Coral bleaching (`rival_boards/rivals_human/coral/20261020_f3b8e3da/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 146 | human_board.json | file | `da45f860cbf6649549924e33c2834edafc0b464aa32643e9bd36860a184665c7` | `rival_boards/rivals_human/coral/20261020_f3b8e3da/human_board.json` |
| 147 | registry file coral.yaml | file | `7e356d61d048f6f81c7d5e16a9ca8541552f268ad4b5cd3b691a824b0787d7c7` | `rivals_code/human_rivals_build/human/registry/coral.yaml` |
| 148 | picks content | content | `ebef5359f26e9e314d445f496c5d00f78c32abc3e7cc228b4f7fa745e2b8ae5a` | recorded in `rival_boards/rivals_human/coral/20261020_f3b8e3da/human_picks.json.lock.json` (`picks_content_sha256`); `rival_boards/human_index/_ledger/f3b8e3daee7474db63e1d10d15b4b93d7044e35408efb31e7611958633e7f362.jsonl` (`picks_content_sha256`); the content of the board's picks file, which is archived |
| 149 | human_picks.json | file | `bef1b5c6fdc4424004f1e32a6dd5e0452dd372b320adbe4b221705aef090364e` | `rival_boards/rivals_human/coral/20261020_f3b8e3da/human_picks.json` |

### Published-rival board, Forest loss (`rival_boards/rivals_human/defo/20261017_d71c61f4/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 150 | human_board.json | file | `d3fc06df8a415cf6f84fb7ab5f2ed5d809e698467fe0b770d0c30c1a6c9aa7f3` | `rival_boards/rivals_human/defo/20261017_d71c61f4/human_board.json` |
| 151 | registry file defo.yaml | file | `fe11acf4a39e9500fda82df15364cf819d3e29734fb9e573c71722b1782baedc` | `rivals_code/human_rivals_build/human/registry/defo.yaml` |
| 152 | picks content | content | `8dd2da0cae0ca287893c849d54bf67e9748bf4efde8c70a157193fc43852fe2a` | recorded in `rival_boards/rivals_human/defo/20261017_d71c61f4/human_picks.json.lock.json` (`picks_content_sha256`); `rival_boards/human_index/_ledger/d71c61f4543fa5b2d54c4de3589eb159cf0d3b4d65b54a677d66413c6b90ccf9.jsonl` (`picks_content_sha256`); the content of the board's picks file, which is archived |
| 153 | human_picks.json | file | `f727030bd520d44e39dad3496816fff2df62db2fc179d2fdf5af02aa5b346fb9` | `rival_boards/rivals_human/defo/20261017_d71c61f4/human_picks.json` |

### Published-rival board, PM2.5 (`rival_boards/rivals_human/pm25/20261007_74e67609/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 154 | human_board.json | file | `7be2a17a4fa1e625dadcf6486db8d92eee9f1125f309ec76dead39782783ce83` | `rival_boards/rivals_human/pm25/20261007_74e67609/human_board.json` |
| 155 | registry file pm25.yaml | file | `5fe8e221190674e5b2d8c972b46acfca819678795d8e48c6600eaf67a3322e2f` | `rivals_code/human_rivals_build/human/registry/pm25.yaml` |
| 156 | picks content | content | `a2e175003b800fd1ad03d5c5d3d829d365848d67b5f955772fe8d2f64de9b9e6` | recorded in `rival_boards/rivals_human/pm25/20261007_74e67609/human_picks.json.lock.json` (`picks_content_sha256`); `rival_boards/human_index/_ledger/74e676096559d7c9fc8bf7d7f62c4909b4c54a16725f80d5b9157bf279808821.jsonl` (`picks_content_sha256`); the content of the board's picks file, which is archived |
| 157 | human_picks.json | file | `3e9adb582e0759e657f1e66cd6540d98576a4f222597b9fa14d3f18706b4c860` | `rival_boards/rivals_human/pm25/20261007_74e67609/human_picks.json` |

### Published-rival board, NDVI (`rival_boards/rivals_human/ndvi/20261016_d1de3158/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 158 | human_board.json | file | `4348e235b2bd375ee6911785e8552c5a2792f0795d7d06d62ce5d4f9c6f08b54` | `rival_boards/rivals_human/ndvi/20261016_d1de3158/human_board.json` |
| 159 | registry file ndvi.yaml | file | `b69537fc7e360da16b5dc60ae827e9a25f509678527695224fa193c20ce5424d` | `rivals_code/human_rivals_build/human/registry/ndvi.yaml` |
| 160 | picks content | content | `409d75e2b670463e3023dec0e3d6828046b505f41efb4b0a3dd8eb24a565ec1f` | recorded in `rival_boards/rivals_human/_moved/20261025_ndvi_board_pre_part618/human_picks.json.lock.json` (`picks_content_sha256`); `rival_boards/rivals_human/ndvi/20261016_d1de3158/human_picks.json.lock.json` (`picks_content_sha256`); `rival_boards/human_index/_ledger/d1de3158cad5ab44a70e5fb6f3cb0956bb268be553e218103c4fb5f58f3bfb8b.jsonl` (`picks_content_sha256`); the content of the board's picks file, which is archived |
| 161 | human_picks.json | file | `29ec54367e6c27421822ac48c47c6fcd8f9d5e01709aa864fc5b65da73ec04da` | `rival_boards/rivals_human/ndvi/20261016_d1de3158/human_picks.json` |

### Published-rival board, NDVI, first rival board (`rival_boards/rivals_human/_moved/20261025_ndvi_board_pre_part618/`)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 162 | human_board.json | file | `ff29caf32a95ea863082090d211eff8a755dcff48eb36c439a114155965a98f2` | `rival_boards/rivals_human/_moved/20261025_ndvi_board_pre_part618/human_board.json` |
| 163 | human_picks.json | file | `c719c574fbbf837176d509f3d85ee3229586491ce56ebb41ebdd4dfd1caea7f7` | `rival_boards/rivals_human/_moved/20261025_ndvi_board_pre_part618/human_picks.json` |

### Published-rival product manifests printed for Part A section 1 (Table S4.9)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 164 | product manifest coral_sst_npz | file | `8252897877061e92375aee4b95ec4a1693a89ce271ecc6842cf2a3e96dce6e70` | `rival_boards/rivals_human/_products/coral_sst_npz/product_manifest.json` |
| 165 | product manifest crw_climatology | file | `d7cbd436c4b462114bc3a9e92997ebfbdef129c752e4c285b80c416ddd179659` | `rival_boards/rivals_human/_products/crw_climatology/product_manifest.json` |
| 166 | product manifest coral_store_20261020 | file | `2e2351f847cb07e2bbf702e67c443a47a1e3b46a26c628db5b63ed56bc239909` | `rival_boards/rivals_human/_products/coral_store_20261020/product_manifest.json` |
| 167 | product manifest noaa_crw_dhw_sitedays | file | `9aa8ae53b61f733dc2d18d63cad2bbcfcae9e41851ca1f6ac62a271d4664ec6d` | `rival_boards/human_products/noaa_crw_dhw_sitedays/v3.1_sitedays_v2_train200_test100_pifsc/product_manifest.json` |
| 168 | product manifest crw_outlook | file | `32b71dfd05790b955e852f9488194c49b9aab4407a49ae2fac1c4faeff4f76e0` | `rival_boards/rivals_human/_products/crw_outlook/product_manifest.json` |
| 169 | product manifest hansen_gfc_v1_13 | file | `5d791b5dd04751bcbb2211c394ecb617042eefaca9fb815782ec6ecd72fe8ab7` | `rival_boards/rivals_human/_products/hansen_gfc_v1_13/product_manifest.json` |
| 170 | product manifest defo_target | file | `40ae28f9db03ffe1da6dfc0771cf430a37c093d3be8fd45a3caec714a4ffd99b` | `rival_boards/rivals_human/_products/defo_target/product_manifest.json` |
| 171 | product manifest defo_static | file | `e69b8ad1d7cd9c99e0ae4f73b0fcd2b05752d247ab9d44c05455f18b8bacd086` | `rival_boards/rivals_human/_products/defo_static/product_manifest.json` |
| 172 | product manifest gadm36_defo42 | file | `fa1508866de13c418af6cd9386e07643ff3f2a08c1189c1b1da15660e6185ba3` | `rival_boards/human_products/gadm/3.6_gpkg_defo42/product_manifest.json` |
| 173 | product manifest defo_vt0007_prep | file | `83df6256a7720c50dc8eb71feb543ee984a2aa0f9edb6b384a43a479713d31b6` | `rival_boards/rivals_human/_moved/20261025T140802690450Z/defo_vt0007_prep/product_manifest.json` |
| 174 | product manifest defo_vt0007_prep, stage test (after the lock) | file | `64de40605a264f9c1ca0359e79e3d9cb809d07bce73029fa487a4004ed575eee` | `rival_boards/rivals_human/_products/defo_vt0007_prep/product_manifest.json` |
| 175 | product manifest pm25_static_cells | file | `c34f865283e1e6ea9f32c2533e2ad2ccf70ce38fa89eb29afbdddb8ad4c9833b` | `rival_boards/rivals_human/_products/pm25_static_cells/product_manifest.json` |
| 176 | product manifest merra2_aer_monthly | file | `da707be1cd431f670fdf07fe079060e4d3307ca5017f66c2e1396ff7625358b0` | `rival_boards/rivals_human/_products/merra2_aer_monthly/product_manifest.json` |
| 177 | product manifest ndvi_static_cells | file | `9c654174472e6192ac6e4b0c1fc0f0d3116ed357bfbe9ac7429b5e9ba3a78900` | `rival_boards/rivals_human/_products/ndvi_static_cells/product_manifest.json` |
| 178 | product manifest ndvi_kraft_store | file | `3ebc2dad12a819fe315c3f04462daa7fe158d7ab91c85c3c869b0ba8773b3a4a` | `rival_boards/rivals_human/_products/ndvi_kraft_store/product_manifest.json` |
| 179 | product manifest monthly_panel | file | `d946f63e972bc69d24723e111871482a98f129a5c1aa07044ef6c534972a3ebc` | `rival_boards/rivals_human/_products/monthly_panel/product_manifest.json` |

### Joined rival table (`rival_boards/rivals_table/20261025T162302876402Z/`) and compact view

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 180 | RIVALS_TABLE.csv | file | `1ccac0e7eb9defc089c31ce382e8a5aa7783a0b12da531813023f19afacc78ba` | `rival_boards/rivals_table/20261025T162302876402Z/RIVALS_TABLE.csv` |
| 181 | RIVALS_TABLE.md | file | `b1bc4de4ef1dfe81edd544eff724d4ce3293d6db87a6ed068c09265752e2c981` | `rival_boards/rivals_table/20261025T162302876402Z/RIVALS_TABLE.md` |
| 182 | inputs_sha256.txt | file | `3c078a44c4f300d90ccb598890db4dd7c849744962fa8c3264d38c09a1cbcf43` | `rival_boards/rivals_table/20261025T162302876402Z/inputs_sha256.txt` |
| 183 | compact view engine/RIVALS_TABLE_FINAL.md (2026-10-27 file) | file | `d27a6b2c03b62aabe88ffc04c580d00d96c6a462765d85b2cf4592c780d435fa` | `engine/RIVALS_TABLE_FINAL.md` |

### Burned-fraction published rivals, Part B, values on 2026-10-27 (unsigned; Table S4.10)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 184 | tool 16a2d736 | recorded | `16a2d7362b83d7d8ddf539a5fe4b75f8166fa56976be3f13d88770fbfd68f591` | recorded in `engine/PENDING_PARTS.md`, Part 621; recomputed from `versions/rival_tool_16a2d736/` (`VERSIONS.md`) |
| 185 | tool 6a635858 | recorded | `6a6358588fa28db55a0ec819002ebbfd53867e0fd17ea76e912b640fd0e1490a` | recorded in `engine/PENDING_PARTS.md`, Part 621, addendum 2; recomputed from `rivals_code/human_rivals_build/human/rivals_human/` and `rivals_code/human_rivals_build/human/adapters/` (`VERSIONS.md`) |
| 186 | registry/fire.yaml (2026-10-27) | file | `bf0b8e55f043b07e85bf85909e7138a34ba1be9da7e517e5cd681475a7336561` | `rivals_code/human_rivals_build/human/registry/fire.yaml` |
| 187 | registry/_products.yaml (2026-10-27) | file | `c7f1ff035d6167258bb5f9993ed3d862836e5858d5339aff2696750c89b8157b` | `rivals_code/human_rivals_build/human/registry/_products.yaml` |
| 188 | production config | file | `0314e9a2ceb02efd84391703f42a6c4eb0974aa47f841341c7afc2cfc358eb97` | `rivals_code/human_rivals_build/human/human_rivals_production.yaml` |
| 189 | DRY config | file | `64ce27ca72c47e8a3f729fb6f2c47b737893736cc8978c72874f5aca34e83355` | `rivals_code/human_rivals_build/human/human_rivals_DRY.yaml` |
| 190 | product manifest fire_static_cells | file | `d44701d16b58607d5a414efc93916f4969e0c2279c66eccbc074117acc4135fe` | `rival_boards/rivals_human/_products/fire_static_cells/product_manifest.json` |
| 191 | product manifest fire_target_2018 | file | `1405f29eb613fd48a2cffff6799046d25f942dc6d93ed5d8b4d401629737a6b6` | `rival_boards/rivals_human/_products/fire_target_2018/product_manifest.json` |
| 192 | product manifest fire_refs_label_store | file | `87e88ad0d0093e24c243db14660ce2de3be3c903991f8345019db09705031b53` | `rival_boards/rivals_human/_products/fire_refs_label_store/product_manifest.json` |
| 193 | slim manifest, lead 0 | file | `786ac653b2c1adfca66f3aab611c563910a2c22765f73930128df86d4c2967cf` | `rival_boards/rivals_human/fire/20261017_869d1f38/slim/lead_0/slim_manifest.json` |
| 194 | slim manifest, lead 6 | file | `3f3d21c3c3d8d399165420af4e00d24f2200129c167abf4d55a2c60e84020699` | `rival_boards/rivals_human/fire/20261017_869d1f38/slim/lead_6/slim_manifest.json` |
| 195 | slim manifest, lead 12 | file | `c138d8a2ba41ef8e4a060e8bbf42cd3afcf11ccf14bb7fb4fbe60d098881ebb5` | `rival_boards/rivals_human/fire/20261017_869d1f38/slim/lead_12/slim_manifest.json` |

### Post hoc analysis code (`analysis/paper_posthoc/`; Table S4.11)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 196 | posthoc_A.py | file | `0cee249c0834dc2bbf0fe9ec458b200e20e096a4c5fc24e8d585a09584bab7c0` | `analysis/paper_posthoc/posthoc_A.py` |
| 197 | posthoc_B.py | file | `6b781c848bd84391da3bb71975135ebdcd806150ec45911d18e2c3f3f0db58ff` | `analysis/paper_posthoc/posthoc_B.py` |
| 198 | reconcile_AB.py | file | `5dcbe687b730c77f6207236bfa674d9a7a473b402e89a6c74b3487c7273b4c58` | `analysis/paper_posthoc/reconcile_AB.py` |
| 199 | SPEC.json | file | `13fc0aaad163db0d3d3d659f381fb6ca84ef668a08b946be43d692972b7de032` | `analysis/paper_posthoc/SPEC.json` |
| 200 | POSTHOC_REPORT.md | file | `b1adbbc17117393d93cdcd0a82002e08fea2f17dc04a3e0f4c377d388044f32a` | `analysis/paper_posthoc/POSTHOC_REPORT.md` |
| 201 | merra2_runaway/sens_A.py | file | `7a6588b810cbeeb19b8e9098e50a3313e6b42d901d80c0178b558685d92f6c3b` | `analysis/paper_posthoc/merra2_runaway/sens_A.py` |
| 202 | merra2_runaway/sens_B.py | file | `5b66f667d14a0a5f4dd9bc65669557b5da08b5ef5b516d4b4dc7256034b47cab` | `analysis/paper_posthoc/merra2_runaway/sens_B.py` |
| 203 | merra2_runaway/sens_A.json | file | `c826c4106671c38278fff328556fdfafef4c40090aba097a55a9ca2462656aba` | `analysis/paper_posthoc/merra2_runaway/sens_A.json` |
| 204 | merra2_runaway/sens_B.json | file | `0679a45e1be536038b7ab153d6e61356927de9b515898ce6b6ea1c754c42ed9f` | `analysis/paper_posthoc/merra2_runaway/sens_B.json` |
| 205 | merra2_formula/SPEC.md | file | `be8948f9d44aa2d5d711ae805eeb6f44f318ec955c156ea18c5a39968870ee68` | `analysis/paper_posthoc/merra2_formula/SPEC.md` |
| 206 | merra2_formula/A/rescore_A.py | file | `e7187fb76cfe7034e6a3bac6f21005d596cf64f57f90016ebb4e8afa12eb879f` | `analysis/paper_posthoc/merra2_formula/A/rescore_A.py` |
| 207 | merra2_formula/A/result_A.json | file | `d5617cc89d54e075d48ea92346fb43a6652d2975a37a94666c7d26dc30707377` | `analysis/paper_posthoc/merra2_formula/A/result_A.json` |
| 208 | merra2_formula/B/rescore_B.py | file | `61c83af4bfbd935d1cd687ee036d45599ac8da47611bb4c0bbc1008a34e628e4` | `analysis/paper_posthoc/merra2_formula/B/rescore_B.py` |
| 209 | merra2_formula/B/result_B.json | file | `6dedad952413167a7f536a9790b950cf169cc25fe7fc804700a1322666902da1` | `analysis/paper_posthoc/merra2_formula/B/result_B.json` |
| 210 | merra2_formula/reconcile/reconcile_AB.py | file | `f3e4bfcbcdd94a9efe97304e92f8300f0cfbcef90fdd51872061ef364a8ed3a4` | `analysis/paper_posthoc/merra2_formula/reconcile/reconcile_AB.py` |
| 211 | merra2_formula/reconcile/reconcile_AB.json | file | `a29a7f6e9e0473df40725973ebf64353a12f91e0e99ce9c931ad961e3a8e9d67` | `analysis/paper_posthoc/merra2_formula/reconcile/reconcile_AB.json` |
| 212 | v2_replay/SPEC.md | file | `9e6743133d75e94b0d3bc4dd1debb5b20f31615fb2c6188d59189abb6ec8d00e` | `analysis/paper_posthoc/v2_replay/SPEC.md` |
| 213 | v2_replay/INPUTS_SHA256.txt | file | `90deaa81977de57867560234975a0725ae3c7a1124b226cb9a629ff16bb7ba79` | `analysis/paper_posthoc/v2_replay/INPUTS_SHA256.txt` |
| 214 | v2_replay/A/replay_A.py | file | `df5d0306879753fafb9c235fd006b9b9645fd39c616462ed5a860d11ceb41316` | `analysis/paper_posthoc/v2_replay/A/replay_A.py` |
| 215 | v2_replay/A/result_A.json | file | `3d04553cf50e19c57f40eab66c9d223fe1fd21e91c48da939111ad216167d7e5` | `analysis/paper_posthoc/v2_replay/A/result_A.json` |
| 216 | v2_replay/B/replay_B.py | file | `42a97b0fa9a8c47833d805e2fa44ef3aa86c352fa9819435a86953f5e9563924` | `analysis/paper_posthoc/v2_replay/B/replay_B.py` |
| 217 | v2_replay/B/result_B.json | file | `258f5c1f7b2a1b7d28452a98b28d07bde4980b773213a92f3a945211ba775a5f` | `analysis/paper_posthoc/v2_replay/B/result_B.json` |
| 218 | v2_replay/reconcile/reconcile_AB.py | file | `6f1fdd715354c377c6f3babc57f29af9cbd78d16b16faaa242287f3ff3fcd620` | `analysis/paper_posthoc/v2_replay/reconcile/reconcile_AB.py` |
| 219 | v2_replay/reconcile/reconcile_AB.json | file | `212dcce934d891641d8572c2203ed3f75c01dc263a78b4b3e4e7826ea60284ae` | `analysis/paper_posthoc/v2_replay/reconcile/reconcile_AB.json` |
| 220 | v2_replay/{A,B}/rows_pm25_lead_0.parquet (identical) | file | `75a95cc667c086159aff6bdf91c788dd3ea4b4f2e1a88ba607634776a3de98ec` | `analysis/paper_posthoc/v2_replay/A/rows_pm25_lead_0.parquet`; identical copies: `analysis/paper_posthoc/v2_replay/B/rows_pm25_lead_0.parquet`, `analysis/paper_posthoc/v2_replay/A/tool_rerun/rows/pm25_20261007_74e67609_lead_0.parquet`, `evidence/engine_v2/replay_af2_20261021/rows/pm25_20261007_74e67609_lead_0.parquet` |
| 221 | v2_replay/{A,B}/rows_pm25_lead_6.parquet (identical) | file | `8c550e1ac24b1e3fb207122a0ade547df3868a8b785abdc2f016e73e7f4b43da` | `analysis/paper_posthoc/v2_replay/A/rows_pm25_lead_6.parquet`; identical copies: `analysis/paper_posthoc/v2_replay/B/rows_pm25_lead_6.parquet` |
| 222 | v2_replay/{A,B}/rows_pm25_lead_12.parquet (identical) | file | `581c3109170d86256959d55e031e55e0ab82ee0e3ff72c8812238445516bb8bf` | `analysis/paper_posthoc/v2_replay/A/rows_pm25_lead_12.parquet`; identical copies: `analysis/paper_posthoc/v2_replay/B/rows_pm25_lead_12.parquet` |
| 223 | v2_replay/{A,B}/rows_ndvi_lead_0.parquet (identical) | file | `a27750f647271a1dfc4750a476ffdeeb5d9a2bc74bc35119174996c35d7349ab` | `analysis/paper_posthoc/v2_replay/A/rows_ndvi_lead_0.parquet`; identical copies: `analysis/paper_posthoc/v2_replay/B/rows_ndvi_lead_0.parquet`, `analysis/paper_posthoc/v2_replay/A/tool_rerun/rows/ndvi_20261016_d1de3158_lead_0.parquet`, `evidence/engine_v2/replay_af2_20261021/rows/ndvi_20261016_d1de3158_lead_0.parquet` |
| 224 | v2_replay/{A,B}/rows_ndvi_lead_6.parquet (identical) | file | `97fb271030b4460de60a4af78efb2b2b2c21122a4d1c5d71a333164d5c2245e8` | `analysis/paper_posthoc/v2_replay/A/rows_ndvi_lead_6.parquet`; identical copies: `analysis/paper_posthoc/v2_replay/B/rows_ndvi_lead_6.parquet` |
| 225 | v2_replay/{A,B}/rows_ndvi_lead_12.parquet (identical) | file | `841a98355af39c9cdb4486f0c3dcbb78987044f31b4d352d873fcee0a17bdd64` | `analysis/paper_posthoc/v2_replay/A/rows_ndvi_lead_12.parquet`; identical copies: `analysis/paper_posthoc/v2_replay/B/rows_ndvi_lead_12.parquet` |
| 226 | v2_replay/{A,B}/rows_fire_lead_0.parquet (identical) | file | `4d039974a9ed629fd51561840dfca8abd665c84c83bf7184a884291be7ee2e3e` | `analysis/paper_posthoc/v2_replay/A/rows_fire_lead_0.parquet`; identical copies: `analysis/paper_posthoc/v2_replay/B/rows_fire_lead_0.parquet`, `analysis/paper_posthoc/v2_replay/A/tool_rerun/rows/fire_20261017_869d1f38_lead_0.parquet`, `evidence/engine_v2/replay_af2_20261021/rows/fire_20261017_869d1f38_lead_0.parquet` |
| 227 | v2_replay/{A,B}/rows_fire_lead_6.parquet (identical) | file | `9807f74736eae58473534eee08bee96d07ea10a6f83a0cbc40aa3dec724180ba` | `analysis/paper_posthoc/v2_replay/A/rows_fire_lead_6.parquet`; identical copies: `analysis/paper_posthoc/v2_replay/B/rows_fire_lead_6.parquet` |
| 228 | v2_replay/{A,B}/rows_fire_lead_12.parquet (identical) | file | `9a878766ebd0aad7962938dcd28adae0ca8a77299a31cd2734204ae4bd92afa0` | `analysis/paper_posthoc/v2_replay/A/rows_fire_lead_12.parquet`; identical copies: `analysis/paper_posthoc/v2_replay/B/rows_fire_lead_12.parquet` |
| 229 | v2_replay/{A,B}/rows_defo_lead_0.parquet (identical) | file | `52c71652c52366acb820df8ce42af34456a66f7eb4ae4a1575aaf30fa18a7ea9` | `analysis/paper_posthoc/v2_replay/A/rows_defo_lead_0.parquet`; identical copies: `analysis/paper_posthoc/v2_replay/B/rows_defo_lead_0.parquet`, `analysis/paper_posthoc/v2_replay/A/tool_rerun/rows/defo_20261017_d71c61f4_lead_0.parquet`, `evidence/engine_v2/replay_af2_20261021/rows/defo_20261017_d71c61f4_lead_0.parquet` |
| 230 | v2_replay/{A,B}/rows_coral_lead_0.parquet (identical) | file | `036f0c4f47c52d0ef2634ec4965d349c839e25c5ea878401dbde25bc2df4e7b6` | **not archived**: coral per-visit replay rows, kept out by ruling AT7 (`KEPT_OUT.md`, A); a reader cannot check this value from the archive |
| 231 | v2_replay/{A,B}/rows_coral_lead_365.parquet (identical) | file | `6683718798ee4b39a88a5c03ec9cae20450d4601ef8e63763870bef1fc643440` | **not archived**: coral per-visit replay rows, kept out by ruling AT7 (`KEPT_OUT.md`, A); a reader cannot check this value from the archive |

### Coral bleaching 2017-2020 sensitivity row, Part 627 (`analysis/coral_sens_2017_2020/`; S4.8; read 2026-11-10)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 232 | lock SENS_LOCK_PREPARED.json (written outside the lock tool) | file | `d0d6bb851fc74bec2205dee7c8fdcc5c8d403a7dca7fa8892c92e1ecd9fba34b` | `analysis/coral_sens_2017_2020/SENS_LOCK_PREPARED.json` |
| 233 | dataset-package fingerprint of the package copy coral_sens_2017_2020 | content | `6a8509e323a7349f1f5e1d6e7861f8c96165af4bcd39e2a9caade425989d76c2` | recorded in `analysis/coral_sens_2017_2020/SENS_LOCK_PREPARED.json` (`package.fingerprint`); `analysis/coral_sens_2017_2020/run/coral_sens_2017_2020/headline/20261029_75f66839/manifest.json` (`package_fingerprint`); recomputed from the package copy `analysis/coral_sens_2017_2020/package/` |
| 234 | run/coral_sens_2017_2020/headline/20261029_75f66839/manifest.json | file | `393e6c2e2da02cb396c5f0ecce2dea62768656087df859701142df7e89fabac9` | `analysis/coral_sens_2017_2020/run/coral_sens_2017_2020/headline/20261029_75f66839/manifest.json` |
| 235 | run/coral_sens_2017_2020/headline/20261029_75f66839/test_preds.parquet | file | `26474c84991676abf7be0db5ee8b469c4ae51c91b26111435549b2f990705f62` | **not archived**: coral per-visit answers, kept out by ruling AT7 (`KEPT_OUT.md`, A); a reader cannot check this value from the archive |

### Post hoc SHAP comparison, Part 628: analysis scripts (`analysis/shap_v1/`; Table S4.11; read 2026-11-17)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 236 | scripts/bardl_shap.py | file | `6bfc9aaf9548ec4b8c3115dca8837201967a4f350cf70dd5fe2f6d581d11a9a1` | `analysis/shap_v1/scripts/bardl_shap.py` |
| 237 | scripts/compare_shap.py | file | `918f099de461902cadd121dcb209ac45353c498eed9266af802ddefe4e56715f` | `analysis/shap_v1/scripts/compare_shap.py` |
| 238 | scripts/make_sample.py | file | `bf524989cf6a37135d1b58c3c60c14dccdf1ff2b52e85f1707f151b1f7ebbe41` | `analysis/shap_v1/scripts/make_sample.py` |
| 239 | scripts/ridge_shap.py | file | `866fd32931ab1da15223c94a10b7c0e47ac5c80ae75b7456a583e69573031c5c` | `analysis/shap_v1/scripts/ridge_shap.py` |
| 240 | scripts/rival_shap.py | file | `a3e836a51e8673012bca9ca26c67a2dac2630c467da0942519bb6ef94572d75e` | `analysis/shap_v1/scripts/rival_shap.py` |
| 241 | scripts/run_shap.py | file | `e99426f189c37385818817844553b1252a7fb0af046f8cec330eaa6f6d7c7170` | `analysis/shap_v1/scripts/run_shap.py` |
| 242 | scripts/shapv1_common.py | file | `85999624da8f1ba38d81453ddbfa1fed49af6843a61bc7d9cf719b31d2b9d812` | `analysis/shap_v1/scripts/shapv1_common.py` |
| 243 | scripts/shapv1_rows.py | file | `2e5fac9e8bf851af288cab81d7db400c2e658aa24f23fcbdbfebdfcc60a51a60` | `analysis/shap_v1/scripts/shapv1_rows.py` |
| 244 | scripts/shapv1_stats.py | file | `20f51cdee626df680d474e59dd84f428e3a1c45d1d6d5166603f1f7c5b2236b9` | `analysis/shap_v1/scripts/shapv1_stats.py` |
| 245 | scripts/shapv1_treeshap.py | file | `22a78b5c5a827cbc8afd5917688b1adffd08e169ed53c10b1390e400f981d961` | `analysis/shap_v1/scripts/shapv1_treeshap.py` |
| 246 | scripts/tr_rebuild.py | file | `b48196273b43ccc877249b00e16e2d4e11d3d09c83bad1eadd3ad200dc782beb` | `analysis/shap_v1/scripts/tr_rebuild.py` |
| 247 | scripts/tr_shap.py | file | `a38b6cb0fcde67ace21ca78ecb48e199ced2f15b8b40522bb1a0a7da27686055` | `analysis/shap_v1/scripts/tr_shap.py` |
| 248 | scripts/tests/diag_coral_exactness.py | file | `c8ab14c5e9484ebb3aa54b187d9720d36f57d0608f2651efcfc154aaf1074bda` | `analysis/shap_v1/scripts/tests/diag_coral_exactness.py` |
| 249 | scripts/tests/smoke_bardl.py | file | `0f7de758dbbaec4689ca38ab0108206aff7b4bb242184faa709a45dddf0a5b79` | `analysis/shap_v1/scripts/tests/smoke_bardl.py` |
| 250 | scripts/tests/smoke_ridge.py | file | `c48f3f66739103099a420cc93ef521be94b9312b7e1164522ee61d94fa36d545` | `analysis/shap_v1/scripts/tests/smoke_ridge.py` |
| 251 | scripts/tests/smoke_unit.py | file | `efdaf76bd3e7f27022e24f933704e19992e34de8bdfcf7fa0022cc743fcfb637` | `analysis/shap_v1/scripts/tests/smoke_unit.py` |
| 252 | scripts/tests/smoke_world.py | file | `560068921cdeb209156cce419cd0059ca029c45f9f8ef7f886b2c115aab0ad8a` | `analysis/shap_v1/scripts/tests/smoke_world.py` |

### Post hoc SHAP comparison, Part 628: the S3.13 table builders' scripts (`analysis/paper/supp_build/s3_13/`; Table S4.11; read 2026-11-17)

| # | Object | Kind | SHA-256 | In the archive |
|---:|---|---|---|---|
| 253 | A/scripts/build_tables.py | file | `847791553e0451fe70ea3066180820aac1d38b2fda41b95fd32305e8986e4c5d` | `analysis/paper/supp_build/s3_13/A/scripts/build_tables.py` |
| 254 | B/scripts/build_tables.py | file | `26c82492b31e8f99a59317919776d8e03451df8274b00d5872f03ee77034c128` | `analysis/paper/supp_build/s3_13/B/scripts/build_tables.py` |
