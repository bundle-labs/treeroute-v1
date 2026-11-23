"""Recomputes the code hashes and the file hashes that this archive lets a reader check.

Python 3.9 (the runs used Python 3.9.13), standard library only:

    py -3.9 VERIFY_HASHES.py                  checks the folder that holds this file
    py -3.9 VERIFY_HASHES.py <folder>         checks another copy of the archive
    py -3.9 VERIFY_HASHES.py --docs <folder>  reads HASH_REGISTER.md and VERSIONS.md from <folder>
                                              (default: the archive folder)

What it checks
  1. Every code version of VERSIONS.md: the hash of its archived folder, formed by the recipe that formed the
     recorded value. A version rebuilt from a later one (an overlay) is checked twice: its written-out folder,
     and the version rebuilt in memory from the archived parts that VERSIONS.md names (the later version, the
     files put back and the files removed); both must give the recorded hash and hold the same files.
  2. The comment-stripped engine code hashes and the engine constants hashes of the five locked treeroute v1
     versions (Table S4.14). The stripped hashes are formed with Python 3.9's tokenizer, which formed the
     recorded values; under another Python version a stripped hash that differs is reported as NOT CHECKED, not
     as a failure. Each constants hash is formed by that version's own treeroute/engine_constants.py, run in a
     separate Python process that writes no bytecode.
  3. Every file hash of Table S4.14 whose file is in the archive (HASH_REGISTER.md), with each identical copy that
     HASH_REGISTER.md names. The three files that ruling AT7 keeps out are listed as not archived.
  4. That HASH_REGISTER.md and VERSIONS.md give the same full values as this file, where they are present.

Not recomputed here: the run and package fingerprints, the derived-settings hashes, the picks contents and the
recorded input-file hashes; HASH_REGISTER.md names the archived records that hold each of them.

Nothing in the archive is written or changed. Exit code 0 when every check passes, 1 otherwise.
"""

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tokenize
from pathlib import PureWindowsPath

sys.dont_write_bytecode = True

CHUNK = 1 << 20

# Data. Every full value below is a value of Table S4.14 (Supplement S4); the archive paths and the
# identical copies are those of HASH_REGISTER.md, and the folders and rebuild steps those of VERSIONS.md.

# Code versions: id, title, recipe, archive folder, how it is archived, Table S4.14 value and entries.
CODE_VERSIONS = [
    {"id": "7b508557", "title": "treeroute v1 engine code", "recipe": "engine", "folder": "versions/ckpt_20261013/engine_before/treeroute", "how": "full copy", "value": "7b5085572574d767e7ef13a2248ac03af9e5f103f0ef49f5e85e9994d9344dbb", "entries": [1]},
    {"id": "1f257395", "title": "treeroute v1 engine code", "recipe": "engine", "folder": "versions/install_20261015/engine_old/treeroute", "how": "full copy", "value": "1f2573957b10b4ddea76bfa38598e35edbc3a593cf2b5eb7b33d1d8e9f386ae1", "entries": [3]},
    {"id": "7a0341ef", "title": "treeroute v1 engine code", "recipe": "engine", "folder": "versions/s_20261016/engine_old/treeroute", "how": "full copy", "value": "7a0341eff4e67759bf12542ad5ab0248bf8b2e56d9d2351a30141f67e44f27b8", "entries": [5]},
    {"id": "65a177bc", "title": "treeroute v1 engine code", "recipe": "engine", "folder": "versions/engine_65a177bc/treeroute", "how": "written out", "value": "65a177bc7cdd47bacca806582bd13be52706ba3da385bb468fe1f0f24b81a0ff", "entries": [7]},
    {"id": "dd7c0984", "title": "treeroute v1 engine code", "recipe": "engine", "folder": "versions/engine_dd7c0984/treeroute", "how": "written out", "value": "dd7c0984d3044aac6cf06d7614df7bd7e8622942580a5f1f0bb08c32ed085d38", "entries": [14]},
    {"id": "930d961c", "title": "treeroute v1 engine code", "recipe": "engine", "folder": "engine/treeroute", "how": "the archived engine", "value": "930d961cdfdd219c36b113174e6c865096f973068e30696850f13d5ec4a60814", "entries": [9]},
    {"id": "f3832db1", "title": "report tooling", "recipe": "report", "folder": "versions/report_tooling_f3832db1/treeroute_report", "how": "written out", "value": "f3832db1896dac4a6962193ea66fbe37cc2f1ea9be3c7c8d10eca8a4bbc4d049", "entries": [19]},
    {"id": "af64f5f0", "title": "report tooling", "recipe": "report", "folder": "versions/report_tooling_af64f5f0/treeroute_report", "how": "written out", "value": "af64f5f013ad194fc5aad3bdc7aa99c22ae90941e24e4353105df9f38299d178", "entries": [20]},
    {"id": "1658e0dd", "title": "report tooling", "recipe": "report", "folder": "engine/treeroute_report", "how": "the archived report tooling", "value": "1658e0ddcf7039e6939fb7ad812885297e025682cf15f29d854d5d98da4b3762", "entries": [21]},
    {"id": "88f4db2c", "title": "treeroute v2 engine code", "recipe": "engine", "folder": "versions/engine_v2/engine/treeroute", "how": "full copy", "value": "88f4db2ce7c0a48834243b8e9403a29d8a3dbcc88c00ed44620d9ced79b44b7d", "entries": [18]},
    {"id": "663ab8ef", "title": "treeroute v2 engine code", "recipe": "engine", "folder": "versions/engine_v2_663ab8ef/treeroute", "how": "written out", "value": "663ab8ef0a666edc786339f2b9e4edac9e067751f72f99ed6a229b903a04bbc3", "entries": [17]},
    {"id": "fc051e5a", "title": "treeroute v2 engine code", "recipe": "engine", "folder": "versions/engine_v2_fc051e5a/treeroute", "how": "written out", "value": "fc051e5ae25177e0bc1ed6003f7d0869eac4e25761b7262f94941a10ca963f6e", "entries": [16]},
    {"id": "46d0306a", "title": "common-rival harness", "recipe": "harness", "folder": "versions/harness_46d0306a/rivals", "how": "written out", "value": "46d0306af3b67f15edf36d8c1fd6ac5e47a1fac06bdf33548b9c88f4decc9485", "entries": [119]},
    {"id": "71457aa9", "title": "common-rival harness", "recipe": "harness", "folder": "versions/harness_71457aa9/rivals", "how": "written out", "value": "71457aa902d30dde17a4a88e8d5c7f1de85515c70d2d7ac4745967066f243b97", "entries": [120]},
    {"id": "b6ea97b7", "title": "common-rival harness", "recipe": "harness", "folder": "rivals_code/rivals_build/rivals", "how": "the archived harness", "value": "b6ea97b72b5a8f79f7f8257f1e4afd00d7783479fada03eea9101410fa509bf2", "entries": [121]},
    {"id": "b9243709", "title": "common-rival export code", "recipe": "export", "folder": "rivals_code/rivals_build/rivals", "how": "the archived export code", "value": "b92437095456333c187567fb8db0787baaa0f5ed1a33d6540190e0198cc98f4d", "entries": [15]},
    {"id": "32ec5df0", "title": "published-rival tool", "recipe": "tool", "folder": "versions/rival_tool_32ec5df0", "how": "written out", "value": "32ec5df06e8022be17393cbd1e6fa2e0929876a1f9835a8b8e707761a13133a5", "entries": [139]},
    {"id": "cd956f1d", "title": "published-rival tool", "recipe": "tool", "folder": "versions/rival_tool_cd956f1d", "how": "written out", "value": "cd956f1dbd0f9b0f2ada37c1a27f8212768d94fc6242cab0686bf7c71608a273", "entries": [142]},
    {"id": "16a2d736", "title": "published-rival tool", "recipe": "tool", "folder": "versions/rival_tool_16a2d736", "how": "written out", "value": "16a2d7362b83d7d8ddf539a5fe4b75f8166fa56976be3f13d88770fbfd68f591", "entries": [184]},
    {"id": "6a635858", "title": "published-rival tool", "recipe": "tool", "folder": "rivals_code/human_rivals_build/human", "how": "the archived tool", "value": "6a6358588fa28db55a0ec819002ebbfd53867e0fd17ea76e912b640fd0e1490a", "entries": [185]},
]

# Overlay versions: the version they are rebuilt from and the steps of VERSIONS.md, in order.
OVERLAYS = {
    "dd7c0984": {"base": "930d961c", "steps": [["put back folder", "versions/engine/_moved_coral_20261020_064437/treeroute", 6]]},
    "65a177bc": {"base": "930d961c", "steps": [["put back folder", "versions/engine/_moved_coral_20261020_064437/treeroute", 6], ["put back folder", "versions/engine/_moved_coral_20261020_014111/treeroute", 13], ["remove", ["check/table.py", "derive/table.py", "labels/rows.py", "package/table.py", "pipeline/table_ladder.py", "pipeline/table_passes.py", "pipeline/table_router.py", "pipeline/table_run.py", "route/neighbour.py"]]]},
    "f3832db1": {"base": "1658e0dd", "steps": [["put back files", {"table.py": "versions/_moved_nested_treeroute_20261015/treeroute_report/treeroute_report/table.py", "continuity_groups.yaml": "versions/_moved_nested_treeroute_20261015/treeroute_report/treeroute_report/continuity_groups.yaml"}]]},
    "af64f5f0": {"base": "1658e0dd", "steps": [["put back files", {"table.py": "versions/engine/_moved_coral_20261020_014111/treeroute_report/table.py", "continuity_groups.yaml": "versions/_moved_nested_treeroute_20261015/treeroute_report/treeroute_report/continuity_groups.yaml"}]]},
    "663ab8ef": {"base": "88f4db2c", "steps": [["put back folder", "versions/engine_v2/_moved/pre_af2_20261021/engine/treeroute", 5]]},
    "fc051e5a": {"base": "663ab8ef", "steps": [["put back folder", "versions/engine_v2/_moved/pre_skeptic_fixes_20261021/treeroute", 3]]},
    "46d0306a": {"base": "b6ea97b7", "steps": [["put back files", {"harness.py": "versions/rivals_build/_moved/20261021_160025_preUnseenFix/harness.py"}]]},
    "71457aa9": {"base": "b6ea97b7", "steps": [["put back files", {"harness.py": "versions/rivals_build/_moved/20261022_070259_preLegalFix/harness.py"}]]},
    "cd956f1d": {"base": "6a635858", "steps": [["put back files", {"rivals_human/maps.py": "versions/human_rivals_build/_moved/20261025T194657Z_partB_baseline/rivals_human/maps.py"}], ["remove", ["adapters/fire_enso.py", "adapters/fire_geff.py", "adapters/fire_lag_common.py", "adapters/fire_refs_prep.py", "adapters/fire_turco.py"]]]},
    "32ec5df0": {"base": "cd956f1d", "steps": [["put back files", {"rivals_human/refs.py": "versions/human_rivals_build/_moved/refs.py.before_offset_fix_20261025"}]]},
    "16a2d736": {"base": "6a635858", "steps": [["put back files", {"adapters/fire_geff.py": "versions/rival_tool_16a2d736/adapters/fire_geff.py"}]]},
}
OVERLAY_ORDER = ["dd7c0984", "65a177bc", "f3832db1", "af64f5f0", "663ab8ef", "fc051e5a", "46d0306a", "71457aa9", "cd956f1d", "32ec5df0", "16a2d736"]

# Comment-stripped engine code of the five locked treeroute v1 versions (folder: the engine files).
STRIPPED = [
    {"id": "7b508557", "entry": 2, "value": "6d19c3e20e8111b82cb10734c776ce3c2135f653f8896575f86260b1863468b6", "folder": "versions/ckpt_20261013/engine_before/treeroute"},
    {"id": "1f257395", "entry": 4, "value": "810eeca7664fc729a95dad5ea3408899812823c39fb4cb802413cc1fcb62fcaa", "folder": "versions/install_20261015/engine_old/treeroute"},
    {"id": "7a0341ef", "entry": 6, "value": "cf566e0549d426ded8adcaa4dbc59f36bc858a755c5cd42726badebd94866024", "folder": "versions/s_20261016/engine_old/treeroute"},
    {"id": "65a177bc", "entry": 8, "value": "13838e41843cf1ec2598a1c3f7383c8ae2371dc094a1f3ec7f63fd7fc073f74a", "folder": "versions/engine_65a177bc/treeroute"},
    {"id": "930d961c", "entry": 10, "value": "85c64b55c02e638cfcb7cefb0fe92af4870d4faed5c21e3f46bbdcbcd0e3a678", "folder": "engine/treeroute"},
]

# Engine constants of the same versions, as each lock records them (folder: holds treeroute/).
CONSTANTS = [
    {"id": "7b508557", "entry": 11, "value": "d1592748460935ec6c2d430357556690d4c69631eff28f028875477ff034207e", "folder": "versions/ckpt_20261013/engine_before"},
    {"id": "1f257395", "entry": 12, "value": "9509bf337328e5935a352ef2f8b112c9a0174df1ba7940b7fd00c5eeb80cee2d", "folder": "versions/install_20261015/engine_old"},
    {"id": "7a0341ef", "entry": 13, "value": "3ef147e5959c04166e3dbcd603723259d9c8ed0adab2d34dd4755662fc1e3a5b", "folder": "versions/s_20261016/engine_old"},
    {"id": "65a177bc", "entry": 13, "value": "3ef147e5959c04166e3dbcd603723259d9c8ed0adab2d34dd4755662fc1e3a5b", "folder": "versions/engine_65a177bc"},
    {"id": "930d961c", "entry": 13, "value": "3ef147e5959c04166e3dbcd603723259d9c8ed0adab2d34dd4755662fc1e3a5b", "folder": "engine"},
]

# File hashes of Table S4.14 whose files are archived: entry, group, object, value, archive path
# and identical copies.
FILES = [
    {"entry": 22, "group": "Report code (S4.6, S4.8)", "object": "coral_report.py", "value": "063be40279a1b4ae0937a21eaec73af98fc4fb379349e34cbdb9c67cf2bacf88", "paths": ["coral_build/report_scripts/coral_report.py"]},
    {"entry": 23, "group": "Report code (S4.6, S4.8)", "object": "make_signed_coral.py (coral package signatures)", "value": "ba096e9c31235c0558c4507c53bf01e90ec380df0eb10d37ea2da164e49f6a75", "paths": ["coral_build/tools/make_signed_coral.py"]},
    {"entry": 27, "group": "Run, PM2.5", "object": "derived.json", "value": "3e2d692b74ad64723fb38c8264e2faa5bdfac8e50a224a141f1d5fb19e10cc36", "paths": ["runs/pm25/headline/20261007_74e67609/derived.json"]},
    {"entry": 28, "group": "Run, PM2.5", "object": "plan.json", "value": "4de95c95a3c55c0737efecc3ba959579bf42e49380df81510a2b9912f1c68779", "paths": ["runs/pm25/headline/20261007_74e67609/plan.json"]},
    {"entry": 33, "group": "Run, PM2.5", "object": "adoption.json", "value": "b6408c90560b458543f0b1d7d46fc7f4c70de110ff2e6e2ad0e8cdef27ec4335", "paths": ["runs/pm25/headline/20261007_74e67609/adoption.json"]},
    {"entry": 34, "group": "Run, PM2.5", "object": "adoption_lead_12.json", "value": "c1987c1e3b1f1f93e379958bafb1a895cbe4b2a61a58ec068356f6ecd520807f", "paths": ["runs/pm25/headline/20261007_74e67609/adoption_lead_12.json"]},
    {"entry": 35, "group": "Run, PM2.5", "object": "adoption_lead_6.json", "value": "7f033ea82f535731fe30940e6aa24b3059562038449b3a75acbff210f39256bf", "paths": ["runs/pm25/headline/20261007_74e67609/adoption_lead_6.json"]},
    {"entry": 39, "group": "Run, NDVI", "object": "derived.json", "value": "8ecc92b58cbd5f65867d477472001085646553c891773ab382fd542c470bb950", "paths": ["runs/ndvi/headline/20261016_d1de3158/derived.json", "evidence/_moved_s_20261016/20261016_580c5b6f/derived.json", "evidence/_moved_install_20261015/superseded_ndvi_plan/20261014_4e505c2b/derived.json", "evidence/ckpt_20261013/superseded_ndvi_plan/20261012_eb4cde0b/derived.json"]},
    {"entry": 40, "group": "Run, NDVI", "object": "plan.json", "value": "c63983fb88f7795c93347b27a413b118515718a044313763c7e1da63b4ce6ab6", "paths": ["runs/ndvi/headline/20261016_d1de3158/plan.json", "evidence/_moved_s_20261016/20261016_580c5b6f/plan.json", "evidence/_moved_install_20261015/superseded_ndvi_plan/20261014_4e505c2b/plan.json", "evidence/ckpt_20261013/superseded_ndvi_plan/20261012_eb4cde0b/plan.json"]},
    {"entry": 45, "group": "Run, NDVI", "object": "adoption.json", "value": "d5ae6f1dd672868166425c6b7590ca911596b29a0c9ccf198feb594623963e59", "paths": ["runs/ndvi/headline/20261016_d1de3158/adoption.json"]},
    {"entry": 46, "group": "Run, NDVI", "object": "adoption_lead_12.json", "value": "e140ea4d28a53229ab4338f497d727767f19b019faae100b817167577a933411", "paths": ["runs/ndvi/headline/20261016_d1de3158/adoption_lead_12.json"]},
    {"entry": 47, "group": "Run, NDVI", "object": "adoption_lead_6.json", "value": "47b35f1da7d3ddc44f483ad1e524bb5c03841ebdd5f41d4d0eb506c225097d4c", "paths": ["runs/ndvi/headline/20261016_d1de3158/adoption_lead_6.json"]},
    {"entry": 51, "group": "Run, Burned fraction", "object": "derived.json", "value": "9255562ca6959e9ec4036021420d47c0545391eb8713bd176d1c8853003c6942", "paths": ["runs/fire/headline/20261017_869d1f38/derived.json"]},
    {"entry": 52, "group": "Run, Burned fraction", "object": "plan.json", "value": "806f3d9bfeed3ccbe17ff7fa3963cd94f836c1de3fda7ec1c3d5abaaf642dfd7", "paths": ["runs/fire/headline/20261017_869d1f38/plan.json"]},
    {"entry": 57, "group": "Run, Burned fraction", "object": "adoption.json", "value": "75f70e5cd22039b62c65f0e4546f669de484edd21d5a9cec581fc0ed774260ad", "paths": ["runs/fire/headline/20261017_869d1f38/adoption.json"]},
    {"entry": 58, "group": "Run, Burned fraction", "object": "adoption_lead_12.json", "value": "baa28a8c8920c20802c0f848acda7b03a8e6b03896e47dcaaf6bdaddf386f52b", "paths": ["runs/fire/headline/20261017_869d1f38/adoption_lead_12.json"]},
    {"entry": 59, "group": "Run, Burned fraction", "object": "adoption_lead_6.json", "value": "f36470a1af96577d9013bbc45c28df743ba5094dbbb4db2d4f63e23e5872c576", "paths": ["runs/fire/headline/20261017_869d1f38/adoption_lead_6.json"]},
    {"entry": 63, "group": "Run, Forest loss", "object": "derived.json", "value": "e17b92cfe8ba31cc6a91afcf52343fdc2bd57ccefbf5c455bea2ef82f133ab16", "paths": ["runs/defo/headline/20261017_d71c61f4/derived.json"]},
    {"entry": 64, "group": "Run, Forest loss", "object": "plan.json", "value": "6ec38e12d9fb684da3a60cf95f18ddf302b42d1bb2b381b534a9a125860366a3", "paths": ["runs/defo/headline/20261017_d71c61f4/plan.json"]},
    {"entry": 69, "group": "Run, Forest loss", "object": "adoption.json", "value": "d8ebdd4cc458b276938bee2bf165088ac9c622f133518031f7c6c806592ee54a", "paths": ["runs/defo/headline/20261017_d71c61f4/adoption.json"]},
    {"entry": 70, "group": "Run, Forest loss", "object": "adoption_lead_1.json", "value": "0e3c1116ebf4d4c47d9dd1ab68bda512db152f105b41dcaf04d2890592486c7b", "paths": ["runs/defo/headline/20261017_d71c61f4/adoption_lead_1.json"]},
    {"entry": 74, "group": "Run, Coral bleaching", "object": "derived.json", "value": "5fd02863f8b91573cf145edc98db7f8b4a9d6a9fd34a1519ef0a0f831e184660", "paths": ["runs/coral/headline/20261020_f3b8e3da/derived.json"]},
    {"entry": 75, "group": "Run, Coral bleaching", "object": "plan.json", "value": "89bd87359d08d02a00faffb91eae0bba02f46704791c35ea3a867b8b7ce39ca7", "paths": ["runs/coral/headline/20261020_f3b8e3da/plan.json"]},
    {"entry": 80, "group": "Run, Coral bleaching", "object": "adoption.json", "value": "2106a36efee4f9fc0650ed7c821a6f8f73c3fdd10c21674f7c8a24b27d80da2f", "paths": ["runs/coral/headline/20261020_f3b8e3da/adoption.json"]},
    {"entry": 81, "group": "Run, Coral bleaching", "object": "adoption_lead_183.json", "value": "0f2d240c37f8e293b40ff3b49048ab0b4345f22ae14edcd9c80df05147eff1fb", "paths": ["runs/coral/headline/20261020_f3b8e3da/adoption_lead_183.json"]},
    {"entry": 82, "group": "Run, Coral bleaching", "object": "adoption_lead_365.json", "value": "3708ac30db065b8f4ed92ec2266dbe44ffb7141e8c25447da92bd6e8a6a654bf", "paths": ["runs/coral/headline/20261020_f3b8e3da/adoption_lead_365.json"]},
    {"entry": 83, "group": "Lock FREEZE_20261006T203115Z, PM2.5", "object": "lock file", "value": "cb41d40c500aa13cea87f8c117598a58f0162fc4e9933c8e2bf919f519f05c9b", "paths": ["records/registry/freeze/FREEZE_20261006T203115Z.lock.json"]},
    {"entry": 84, "group": "Lock FREEZE_20261006T203115Z, PM2.5", "object": "protocol document", "value": "d1d6abaadf200bd2e8b76ce5ffeba2818d15816325d4648bfea811ee4a87a12d", "paths": ["records/registry/freeze/PREREGISTRATION_20261006T203115Z.md"]},
    {"entry": 86, "group": "Lock FREEZE_20261007T130812Z, burned fraction", "object": "lock file", "value": "d77da0b854f86e0c96b3e2a994d942f2d5199cd8cdaba5d9c9ec55df0d368d66", "paths": ["records/registry/freeze/FREEZE_20261007T130812Z.lock.json"]},
    {"entry": 87, "group": "Lock FREEZE_20261007T130812Z, burned fraction", "object": "protocol document", "value": "347d031107b1ab0bb1d972d705f96f5ae5a9ac12a4586872cb389db48a904197", "paths": ["records/registry/freeze/PREREGISTRATION_20261007T130812Z.md"]},
    {"entry": 89, "group": "Lock FREEZE_20261007T132431Z, NDVI", "object": "lock file", "value": "7b34725519b5d9332f094ede777a35f000b5427af130b256871ad250d73a0744", "paths": ["records/registry/freeze/FREEZE_20261007T132431Z.lock.json"]},
    {"entry": 90, "group": "Lock FREEZE_20261007T132431Z, NDVI", "object": "protocol document", "value": "8c3003344d350b71ce0b84aeecc2aa1979e827a5be2b14d35ad032cfbff46866", "paths": ["records/registry/freeze/PREREGISTRATION_20261007T132431Z.md"]},
    {"entry": 92, "group": "Lock FREEZE_20261013T102938Z, burned fraction", "object": "lock file", "value": "204040c8f1194131c1903c17abd855521f4db122053a59a3c2975ebe24cd5d93", "paths": ["records/registry/freeze/FREEZE_20261013T102938Z.lock.json"]},
    {"entry": 93, "group": "Lock FREEZE_20261013T102938Z, burned fraction", "object": "protocol document", "value": "1654e538625da509e641dd69bf0bf098e64a98a7e18f6506cce03e4e7abf22b9", "paths": ["records/registry/freeze/PREREGISTRATION_20261013T102938Z.md"]},
    {"entry": 95, "group": "Lock FREEZE_20261013T103700Z, NDVI", "object": "lock file", "value": "4b4606e59443e24123c05694fa186d36ec0b4e790a03f89cc33c70ff607289d9", "paths": ["records/registry/freeze/FREEZE_20261013T103700Z.lock.json"]},
    {"entry": 96, "group": "Lock FREEZE_20261013T103700Z, NDVI", "object": "protocol document", "value": "9bd51d5529b4459f3432611c94a97ec0a9a4c94b371c1c1932013cdeac55ae09", "paths": ["records/registry/freeze/PREREGISTRATION_20261013T103700Z.md"]},
    {"entry": 98, "group": "Lock FREEZE_20261016T012320Z, NDVI", "object": "lock file", "value": "b2da313aa4ccef5b42d8156d4f72432387de87bfec04b1f882ca81754259134b", "paths": ["records/registry/freeze/FREEZE_20261016T012320Z.lock.json"]},
    {"entry": 99, "group": "Lock FREEZE_20261016T012320Z, NDVI", "object": "protocol document", "value": "f41a0fbda9f402c437f2b794375963f4a414eb64b9b358ab289ef639912bc4c4", "paths": ["records/registry/freeze/PREREGISTRATION_20261016T012320Z.md"]},
    {"entry": 101, "group": "Lock FREEZE_20261016T012828Z, burned fraction", "object": "lock file", "value": "184e9c7c55525cfc5028dc459ddc8083fa604deba53133e4fc639b9980590b3a", "paths": ["records/registry/freeze/FREEZE_20261016T012828Z.lock.json"]},
    {"entry": 102, "group": "Lock FREEZE_20261016T012828Z, burned fraction", "object": "protocol document", "value": "4ebf028ceeddfb9bd1197d6691b3fc1c6676df8e6e1a273433b8b39ed332711f", "paths": ["records/registry/freeze/PREREGISTRATION_20261016T012828Z.md"]},
    {"entry": 104, "group": "Lock FREEZE_20261016T090651Z, NDVI", "object": "lock file", "value": "960bc7d51829d93bc72bf4b0055fff44500f1208543c4157c81ccce869fbab99", "paths": ["records/registry/freeze/FREEZE_20261016T090651Z.lock.json"]},
    {"entry": 105, "group": "Lock FREEZE_20261016T090651Z, NDVI", "object": "protocol document", "value": "1b757ac7745e14da6b78a0919d70ee10c654b855ec33bc457aa53d94752d0bb7", "paths": ["records/registry/freeze/PREREGISTRATION_20261016T090651Z.md"]},
    {"entry": 107, "group": "Lock FREEZE_20261016T091126Z, burned fraction", "object": "lock file", "value": "f8c297e5ff761c901c54efccfb25530d67dd37d623737b0954e2492d49470aa7", "paths": ["records/registry/freeze/FREEZE_20261016T091126Z.lock.json"]},
    {"entry": 108, "group": "Lock FREEZE_20261016T091126Z, burned fraction", "object": "protocol document", "value": "89d97c8020f7cddac397cc6b5d7f238e60ef5509ab1adcb9b8bb8aa84e24db8e", "paths": ["records/registry/freeze/PREREGISTRATION_20261016T091126Z.md"]},
    {"entry": 110, "group": "Lock FREEZE_20261017T105545Z, forest loss", "object": "lock file", "value": "a59408bb2f40a8987b3cc407930ab6d944dc3fe2a92c32cb19c3a9766d26e0e9", "paths": ["records/registry/freeze/FREEZE_20261017T105545Z.lock.json"]},
    {"entry": 111, "group": "Lock FREEZE_20261017T105545Z, forest loss", "object": "protocol document", "value": "20e879c198257e5a03f8697eabc18db4bcc77c704760f09a1b90658654c2df92", "paths": ["records/registry/freeze/PREREGISTRATION_20261017T105545Z.md"]},
    {"entry": 113, "group": "Lock FREEZE_20261020T100907Z, coral bleaching", "object": "lock file", "value": "70b163cd8ac671f554cb18101f433c64e7d047f40226434320bc45a1f5620567", "paths": ["records/registry/freeze/FREEZE_20261020T100907Z.lock.json"]},
    {"entry": 114, "group": "Lock FREEZE_20261020T100907Z, coral bleaching", "object": "protocol document", "value": "2b644584910b55cd785f0d6f52d11bd5df9a8899de1f66e4e54a57599fd740f4", "paths": ["records/registry/freeze/PREREGISTRATION_20261020T100907Z.md"]},
    {"entry": 116, "group": "Signature records", "object": "coral protocol document signature record", "value": "611db73093e719179e06c877c9d7d9aecca0e76f1a6340873366ae5233822e0b", "paths": ["records/registry/freeze/PREREGISTRATION_20261020T100907Z.SIGNED.md"]},
    {"entry": 117, "group": "Signature records", "object": "common-rival protocol signature record", "value": "5bf9e92b3de6ef74262e270aaa169fabc1ad4b5fcde0f52b4c6f4cca27c88a3b", "paths": ["records/registry/rivals/PREREGISTRATION_rivals_common_20261021T125123Z.SIGNED.md"]},
    {"entry": 118, "group": "Signature records", "object": "Part A signature record", "value": "a4d663dae47212c24d634208273e8ad0395b8182c1b6fb26214cd80c27f4cb28", "paths": ["records/registry/rivals/PREREGISTRATION_human_partA_20261025T105940Z.SIGNED.txt"]},
    {"entry": 122, "group": "Common-rival harness and protocol (S4.7.1)", "object": "signed common-rival protocol document", "value": "91c62b07dbc9505dcc3b7391cef3722ece97c29b6140de7e73e8b1b83dd95bb5", "paths": ["records/registry/rivals/PREREGISTRATION_rivals_common_20261021T125123Z.md", "rivals_code/rivals_build/PREREGISTRATION_DRAFT_rivals_common.md"]},
    {"entry": 123, "group": "Common-rival board, Coral bleaching", "object": "board.json", "value": "61a2482d0133a1aa3a01d8eab6f8e0a1a3d0c10c6cdc485d2731abb06fb931ec", "paths": ["rival_boards/rivals/coral/20261020_f3b8e3da/board.json"]},
    {"entry": 125, "group": "Common-rival board, Coral bleaching", "object": "picks.json", "value": "e152553533151f172671b2f4c59ef4ee2bbe1ff4dde625a239d22c477f12a6f8", "paths": ["rival_boards/rivals/coral/20261020_f3b8e3da/picks.json"]},
    {"entry": 126, "group": "Common-rival board, Coral bleaching", "object": "picks.json of the first rival board (46d0306a; moved aside)", "value": "8492c4f2377f917542e431dd7f253f20f4c488f567f9486f213978a7bec5d0b5", "paths": ["rival_boards/rivals_build/_moved/coral_board_pre_fix599_20261021_160319/20261020_f3b8e3da/picks.json"]},
    {"entry": 127, "group": "Common-rival board, Burned fraction", "object": "board.json", "value": "b9f59f9e397a0009404fe161773d801e809b910a95c3812b852e33cab9cd958b", "paths": ["rival_boards/rivals/fire/20261017_869d1f38/board.json"]},
    {"entry": 129, "group": "Common-rival board, Burned fraction", "object": "picks.json", "value": "33f9e968ea7c01dc8e764d89cfa8fd801fbb721395ecdc577c9e722dbabac207", "paths": ["rival_boards/rivals/fire/20261017_869d1f38/picks.json"]},
    {"entry": 130, "group": "Common-rival board, PM2.5", "object": "board.json", "value": "b2bcf4152f91c7ab2968f435d59fb9154d650431c2f83a874c0034cb59e01be0", "paths": ["rival_boards/rivals/pm25/20261007_74e67609/board.json"]},
    {"entry": 132, "group": "Common-rival board, PM2.5", "object": "picks.json", "value": "4b567830a4ace95e2b5b5e11128ac6fe374a897364fccc67037b853db3fb27fc", "paths": ["rival_boards/rivals/pm25/20261007_74e67609/picks.json"]},
    {"entry": 133, "group": "Common-rival board, Forest loss", "object": "board.json", "value": "440e86a78d1ec69d17b2bbd119ddce8490769d689601ad7ffc1f3719922a4f6d", "paths": ["rival_boards/rivals/defo/20261017_d71c61f4/board.json"]},
    {"entry": 135, "group": "Common-rival board, Forest loss", "object": "picks.json", "value": "08b1678703fcf30bfdcaeec003010a97a5311c1813c9e6e3282325f77e44cc5c", "paths": ["rival_boards/rivals/defo/20261017_d71c61f4/picks.json"]},
    {"entry": 136, "group": "Common-rival board, NDVI", "object": "board.json", "value": "f19d11444254b7d0afdff9df6fca4ca710de14a3c11b78dbcd609f451cbe4b87", "paths": ["rival_boards/rivals/ndvi/20261016_d1de3158/board.json"]},
    {"entry": 138, "group": "Common-rival board, NDVI", "object": "picks.json", "value": "852aa1bfbf3ca3085f4700cc55e2bbd76bd5d6abae8e015ca0ea2fd5512ffbd6", "paths": ["rival_boards/rivals/ndvi/20261016_d1de3158/picks.json"]},
    {"entry": 140, "group": "Published-rival tool, registries and protocol", "object": "registry schema (_schema.yaml) a3cda623", "value": "a3cda6238677d3f13fd4a324e43dfc4b982a26d999f80baf200b9f4e49a33c61", "paths": ["rivals_code/human_rivals_build/pt/ag/full1/grid_ok0/_registry_dry/_schema.yaml"]},
    {"entry": 141, "group": "Published-rival tool, registries and protocol", "object": "product registry (_products.yaml) 4e479759", "value": "4e4797597c0a7c76815159d7ce5fa3cf723d2b996d1e3b67a05968136bcb5d1f", "paths": ["versions/human_rivals_build/_moved/20261025T194657Z_partB_baseline/registry/_products.yaml", "versions/human_rivals_build/_moved/20261022_review_fixes_before/registry___products.yaml"]},
    {"entry": 143, "group": "Published-rival tool, registries and protocol", "object": "registry schema (_schema.yaml) 0d4dbcb7", "value": "0d4dbcb7d81e32b901c35395df3fc4f78619493a9d18bb52711f3c6daf7b8ced", "paths": ["rivals_code/human_rivals_build/human/registry/_schema.yaml"]},
    {"entry": 144, "group": "Published-rival tool, registries and protocol", "object": "NDVI registry file at the Part A signature (ndvi.yaml)", "value": "e24195f1a89454abbeb3aa0a406372849aad28c53d90bb80eb0255b2327d1d58", "paths": ["versions/rival_tool_registry_part_a/ndvi.yaml"]},
    {"entry": 145, "group": "Published-rival tool, registries and protocol", "object": "signed published-rival protocol document (Part A)", "value": "4db899658f22e30d50e12980b4db66e947b9cdb519fab8b52817968e477360b8", "paths": ["records/registry/rivals/PREREGISTRATION_human_partA_20261025T105940Z.txt", "rivals_code/human_rivals_build/PREREGISTRATION_DRAFT_human_partA.txt"]},
    {"entry": 146, "group": "Published-rival board, Coral bleaching", "object": "human_board.json", "value": "da45f860cbf6649549924e33c2834edafc0b464aa32643e9bd36860a184665c7", "paths": ["rival_boards/rivals_human/coral/20261020_f3b8e3da/human_board.json"]},
    {"entry": 147, "group": "Published-rival board, Coral bleaching", "object": "registry file coral.yaml", "value": "7e356d61d048f6f81c7d5e16a9ca8541552f268ad4b5cd3b691a824b0787d7c7", "paths": ["rivals_code/human_rivals_build/human/registry/coral.yaml"]},
    {"entry": 149, "group": "Published-rival board, Coral bleaching", "object": "human_picks.json", "value": "bef1b5c6fdc4424004f1e32a6dd5e0452dd372b320adbe4b221705aef090364e", "paths": ["rival_boards/rivals_human/coral/20261020_f3b8e3da/human_picks.json"]},
    {"entry": 150, "group": "Published-rival board, Forest loss", "object": "human_board.json", "value": "d3fc06df8a415cf6f84fb7ab5f2ed5d809e698467fe0b770d0c30c1a6c9aa7f3", "paths": ["rival_boards/rivals_human/defo/20261017_d71c61f4/human_board.json"]},
    {"entry": 151, "group": "Published-rival board, Forest loss", "object": "registry file defo.yaml", "value": "fe11acf4a39e9500fda82df15364cf819d3e29734fb9e573c71722b1782baedc", "paths": ["rivals_code/human_rivals_build/human/registry/defo.yaml"]},
    {"entry": 153, "group": "Published-rival board, Forest loss", "object": "human_picks.json", "value": "f727030bd520d44e39dad3496816fff2df62db2fc179d2fdf5af02aa5b346fb9", "paths": ["rival_boards/rivals_human/defo/20261017_d71c61f4/human_picks.json"]},
    {"entry": 154, "group": "Published-rival board, PM2.5", "object": "human_board.json", "value": "7be2a17a4fa1e625dadcf6486db8d92eee9f1125f309ec76dead39782783ce83", "paths": ["rival_boards/rivals_human/pm25/20261007_74e67609/human_board.json"]},
    {"entry": 155, "group": "Published-rival board, PM2.5", "object": "registry file pm25.yaml", "value": "5fe8e221190674e5b2d8c972b46acfca819678795d8e48c6600eaf67a3322e2f", "paths": ["rivals_code/human_rivals_build/human/registry/pm25.yaml"]},
    {"entry": 157, "group": "Published-rival board, PM2.5", "object": "human_picks.json", "value": "3e9adb582e0759e657f1e66cd6540d98576a4f222597b9fa14d3f18706b4c860", "paths": ["rival_boards/rivals_human/pm25/20261007_74e67609/human_picks.json"]},
    {"entry": 158, "group": "Published-rival board, NDVI", "object": "human_board.json", "value": "4348e235b2bd375ee6911785e8552c5a2792f0795d7d06d62ce5d4f9c6f08b54", "paths": ["rival_boards/rivals_human/ndvi/20261016_d1de3158/human_board.json"]},
    {"entry": 159, "group": "Published-rival board, NDVI", "object": "registry file ndvi.yaml", "value": "b69537fc7e360da16b5dc60ae827e9a25f509678527695224fa193c20ce5424d", "paths": ["rivals_code/human_rivals_build/human/registry/ndvi.yaml"]},
    {"entry": 161, "group": "Published-rival board, NDVI", "object": "human_picks.json", "value": "29ec54367e6c27421822ac48c47c6fcd8f9d5e01709aa864fc5b65da73ec04da", "paths": ["rival_boards/rivals_human/ndvi/20261016_d1de3158/human_picks.json"]},
    {"entry": 162, "group": "Published-rival board, NDVI, first rival board", "object": "human_board.json", "value": "ff29caf32a95ea863082090d211eff8a755dcff48eb36c439a114155965a98f2", "paths": ["rival_boards/rivals_human/_moved/20261025_ndvi_board_pre_part618/human_board.json"]},
    {"entry": 163, "group": "Published-rival board, NDVI, first rival board", "object": "human_picks.json", "value": "c719c574fbbf837176d509f3d85ee3229586491ce56ebb41ebdd4dfd1caea7f7", "paths": ["rival_boards/rivals_human/_moved/20261025_ndvi_board_pre_part618/human_picks.json"]},
    {"entry": 164, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest coral_sst_npz", "value": "8252897877061e92375aee4b95ec4a1693a89ce271ecc6842cf2a3e96dce6e70", "paths": ["rival_boards/rivals_human/_products/coral_sst_npz/product_manifest.json"]},
    {"entry": 165, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest crw_climatology", "value": "d7cbd436c4b462114bc3a9e92997ebfbdef129c752e4c285b80c416ddd179659", "paths": ["rival_boards/rivals_human/_products/crw_climatology/product_manifest.json"]},
    {"entry": 166, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest coral_store_20261020", "value": "2e2351f847cb07e2bbf702e67c443a47a1e3b46a26c628db5b63ed56bc239909", "paths": ["rival_boards/rivals_human/_products/coral_store_20261020/product_manifest.json"]},
    {"entry": 167, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest noaa_crw_dhw_sitedays", "value": "9aa8ae53b61f733dc2d18d63cad2bbcfcae9e41851ca1f6ac62a271d4664ec6d", "paths": ["rival_boards/human_products/noaa_crw_dhw_sitedays/v3.1_sitedays_v2_train200_test100_pifsc/product_manifest.json"]},
    {"entry": 168, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest crw_outlook", "value": "32b71dfd05790b955e852f9488194c49b9aab4407a49ae2fac1c4faeff4f76e0", "paths": ["rival_boards/rivals_human/_products/crw_outlook/product_manifest.json"]},
    {"entry": 169, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest hansen_gfc_v1_13", "value": "5d791b5dd04751bcbb2211c394ecb617042eefaca9fb815782ec6ecd72fe8ab7", "paths": ["rival_boards/rivals_human/_products/hansen_gfc_v1_13/product_manifest.json"]},
    {"entry": 170, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest defo_target", "value": "40ae28f9db03ffe1da6dfc0771cf430a37c093d3be8fd45a3caec714a4ffd99b", "paths": ["rival_boards/rivals_human/_products/defo_target/product_manifest.json"]},
    {"entry": 171, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest defo_static", "value": "e69b8ad1d7cd9c99e0ae4f73b0fcd2b05752d247ab9d44c05455f18b8bacd086", "paths": ["rival_boards/rivals_human/_products/defo_static/product_manifest.json"]},
    {"entry": 172, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest gadm36_defo42", "value": "fa1508866de13c418af6cd9386e07643ff3f2a08c1189c1b1da15660e6185ba3", "paths": ["rival_boards/human_products/gadm/3.6_gpkg_defo42/product_manifest.json"]},
    {"entry": 173, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest defo_vt0007_prep", "value": "83df6256a7720c50dc8eb71feb543ee984a2aa0f9edb6b384a43a479713d31b6", "paths": ["rival_boards/rivals_human/_moved/20261025T140802690450Z/defo_vt0007_prep/product_manifest.json"]},
    {"entry": 174, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest defo_vt0007_prep, stage test (after the lock)", "value": "64de40605a264f9c1ca0359e79e3d9cb809d07bce73029fa487a4004ed575eee", "paths": ["rival_boards/rivals_human/_products/defo_vt0007_prep/product_manifest.json"]},
    {"entry": 175, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest pm25_static_cells", "value": "c34f865283e1e6ea9f32c2533e2ad2ccf70ce38fa89eb29afbdddb8ad4c9833b", "paths": ["rival_boards/rivals_human/_products/pm25_static_cells/product_manifest.json"]},
    {"entry": 176, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest merra2_aer_monthly", "value": "da707be1cd431f670fdf07fe079060e4d3307ca5017f66c2e1396ff7625358b0", "paths": ["rival_boards/rivals_human/_products/merra2_aer_monthly/product_manifest.json"]},
    {"entry": 177, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest ndvi_static_cells", "value": "9c654174472e6192ac6e4b0c1fc0f0d3116ed357bfbe9ac7429b5e9ba3a78900", "paths": ["rival_boards/rivals_human/_products/ndvi_static_cells/product_manifest.json"]},
    {"entry": 178, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest ndvi_kraft_store", "value": "3ebc2dad12a819fe315c3f04462daa7fe158d7ab91c85c3c869b0ba8773b3a4a", "paths": ["rival_boards/rivals_human/_products/ndvi_kraft_store/product_manifest.json"]},
    {"entry": 179, "group": "Published-rival product manifests printed for Part A section 1 (Table S4.9)", "object": "product manifest monthly_panel", "value": "d946f63e972bc69d24723e111871482a98f129a5c1aa07044ef6c534972a3ebc", "paths": ["rival_boards/rivals_human/_products/monthly_panel/product_manifest.json"]},
    {"entry": 180, "group": "Joined rival table", "object": "RIVALS_TABLE.csv", "value": "1ccac0e7eb9defc089c31ce382e8a5aa7783a0b12da531813023f19afacc78ba", "paths": ["rival_boards/rivals_table/20261025T162302876402Z/RIVALS_TABLE.csv"]},
    {"entry": 181, "group": "Joined rival table", "object": "RIVALS_TABLE.md", "value": "b1bc4de4ef1dfe81edd544eff724d4ce3293d6db87a6ed068c09265752e2c981", "paths": ["rival_boards/rivals_table/20261025T162302876402Z/RIVALS_TABLE.md"]},
    {"entry": 182, "group": "Joined rival table", "object": "inputs_sha256.txt", "value": "3c078a44c4f300d90ccb598890db4dd7c849744962fa8c3264d38c09a1cbcf43", "paths": ["rival_boards/rivals_table/20261025T162302876402Z/inputs_sha256.txt"]},
    {"entry": 183, "group": "Joined rival table", "object": "compact view engine/RIVALS_TABLE_FINAL.md (2026-10-27 file)", "value": "d27a6b2c03b62aabe88ffc04c580d00d96c6a462765d85b2cf4592c780d435fa", "paths": ["engine/RIVALS_TABLE_FINAL.md"]},
    {"entry": 186, "group": "Burned-fraction published rivals, Part B, values on 2026-10-27 (unsigned; Table S4.10)", "object": "registry/fire.yaml (2026-10-27)", "value": "bf0b8e55f043b07e85bf85909e7138a34ba1be9da7e517e5cd681475a7336561", "paths": ["rivals_code/human_rivals_build/human/registry/fire.yaml"]},
    {"entry": 187, "group": "Burned-fraction published rivals, Part B, values on 2026-10-27 (unsigned; Table S4.10)", "object": "registry/_products.yaml (2026-10-27)", "value": "c7f1ff035d6167258bb5f9993ed3d862836e5858d5339aff2696750c89b8157b", "paths": ["rivals_code/human_rivals_build/human/registry/_products.yaml"]},
    {"entry": 188, "group": "Burned-fraction published rivals, Part B, values on 2026-10-27 (unsigned; Table S4.10)", "object": "production config", "value": "0314e9a2ceb02efd84391703f42a6c4eb0974aa47f841341c7afc2cfc358eb97", "paths": ["rivals_code/human_rivals_build/human/human_rivals_production.yaml"]},
    {"entry": 189, "group": "Burned-fraction published rivals, Part B, values on 2026-10-27 (unsigned; Table S4.10)", "object": "DRY config", "value": "64ce27ca72c47e8a3f729fb6f2c47b737893736cc8978c72874f5aca34e83355", "paths": ["rivals_code/human_rivals_build/human/human_rivals_DRY.yaml"]},
    {"entry": 190, "group": "Burned-fraction published rivals, Part B, values on 2026-10-27 (unsigned; Table S4.10)", "object": "product manifest fire_static_cells", "value": "d44701d16b58607d5a414efc93916f4969e0c2279c66eccbc074117acc4135fe", "paths": ["rival_boards/rivals_human/_products/fire_static_cells/product_manifest.json"]},
    {"entry": 191, "group": "Burned-fraction published rivals, Part B, values on 2026-10-27 (unsigned; Table S4.10)", "object": "product manifest fire_target_2018", "value": "1405f29eb613fd48a2cffff6799046d25f942dc6d93ed5d8b4d401629737a6b6", "paths": ["rival_boards/rivals_human/_products/fire_target_2018/product_manifest.json"]},
    {"entry": 192, "group": "Burned-fraction published rivals, Part B, values on 2026-10-27 (unsigned; Table S4.10)", "object": "product manifest fire_refs_label_store", "value": "87e88ad0d0093e24c243db14660ce2de3be3c903991f8345019db09705031b53", "paths": ["rival_boards/rivals_human/_products/fire_refs_label_store/product_manifest.json"]},
    {"entry": 193, "group": "Burned-fraction published rivals, Part B, values on 2026-10-27 (unsigned; Table S4.10)", "object": "slim manifest, lead 0", "value": "786ac653b2c1adfca66f3aab611c563910a2c22765f73930128df86d4c2967cf", "paths": ["rival_boards/rivals_human/fire/20261017_869d1f38/slim/lead_0/slim_manifest.json"]},
    {"entry": 194, "group": "Burned-fraction published rivals, Part B, values on 2026-10-27 (unsigned; Table S4.10)", "object": "slim manifest, lead 6", "value": "3f3d21c3c3d8d399165420af4e00d24f2200129c167abf4d55a2c60e84020699", "paths": ["rival_boards/rivals_human/fire/20261017_869d1f38/slim/lead_6/slim_manifest.json"]},
    {"entry": 195, "group": "Burned-fraction published rivals, Part B, values on 2026-10-27 (unsigned; Table S4.10)", "object": "slim manifest, lead 12", "value": "c138d8a2ba41ef8e4a060e8bbf42cd3afcf11ccf14bb7fb4fbe60d098881ebb5", "paths": ["rival_boards/rivals_human/fire/20261017_869d1f38/slim/lead_12/slim_manifest.json"]},
    {"entry": 196, "group": "Post hoc analysis code", "object": "posthoc_A.py", "value": "0cee249c0834dc2bbf0fe9ec458b200e20e096a4c5fc24e8d585a09584bab7c0", "paths": ["analysis/paper_posthoc/posthoc_A.py"]},
    {"entry": 197, "group": "Post hoc analysis code", "object": "posthoc_B.py", "value": "6b781c848bd84391da3bb71975135ebdcd806150ec45911d18e2c3f3f0db58ff", "paths": ["analysis/paper_posthoc/posthoc_B.py"]},
    {"entry": 198, "group": "Post hoc analysis code", "object": "reconcile_AB.py", "value": "5dcbe687b730c77f6207236bfa674d9a7a473b402e89a6c74b3487c7273b4c58", "paths": ["analysis/paper_posthoc/reconcile_AB.py"]},
    {"entry": 199, "group": "Post hoc analysis code", "object": "SPEC.json", "value": "13fc0aaad163db0d3d3d659f381fb6ca84ef668a08b946be43d692972b7de032", "paths": ["analysis/paper_posthoc/SPEC.json"]},
    {"entry": 200, "group": "Post hoc analysis code", "object": "POSTHOC_REPORT.md", "value": "b1adbbc17117393d93cdcd0a82002e08fea2f17dc04a3e0f4c377d388044f32a", "paths": ["analysis/paper_posthoc/POSTHOC_REPORT.md"]},
    {"entry": 201, "group": "Post hoc analysis code", "object": "merra2_runaway/sens_A.py", "value": "7a6588b810cbeeb19b8e9098e50a3313e6b42d901d80c0178b558685d92f6c3b", "paths": ["analysis/paper_posthoc/merra2_runaway/sens_A.py"]},
    {"entry": 202, "group": "Post hoc analysis code", "object": "merra2_runaway/sens_B.py", "value": "5b66f667d14a0a5f4dd9bc65669557b5da08b5ef5b516d4b4dc7256034b47cab", "paths": ["analysis/paper_posthoc/merra2_runaway/sens_B.py"]},
    {"entry": 203, "group": "Post hoc analysis code", "object": "merra2_runaway/sens_A.json", "value": "c826c4106671c38278fff328556fdfafef4c40090aba097a55a9ca2462656aba", "paths": ["analysis/paper_posthoc/merra2_runaway/sens_A.json"]},
    {"entry": 204, "group": "Post hoc analysis code", "object": "merra2_runaway/sens_B.json", "value": "0679a45e1be536038b7ab153d6e61356927de9b515898ce6b6ea1c754c42ed9f", "paths": ["analysis/paper_posthoc/merra2_runaway/sens_B.json"]},
    {"entry": 205, "group": "Post hoc analysis code", "object": "merra2_formula/SPEC.md", "value": "be8948f9d44aa2d5d711ae805eeb6f44f318ec955c156ea18c5a39968870ee68", "paths": ["analysis/paper_posthoc/merra2_formula/SPEC.md"]},
    {"entry": 206, "group": "Post hoc analysis code", "object": "merra2_formula/A/rescore_A.py", "value": "e7187fb76cfe7034e6a3bac6f21005d596cf64f57f90016ebb4e8afa12eb879f", "paths": ["analysis/paper_posthoc/merra2_formula/A/rescore_A.py"]},
    {"entry": 207, "group": "Post hoc analysis code", "object": "merra2_formula/A/result_A.json", "value": "d5617cc89d54e075d48ea92346fb43a6652d2975a37a94666c7d26dc30707377", "paths": ["analysis/paper_posthoc/merra2_formula/A/result_A.json"]},
    {"entry": 208, "group": "Post hoc analysis code", "object": "merra2_formula/B/rescore_B.py", "value": "61c83af4bfbd935d1cd687ee036d45599ac8da47611bb4c0bbc1008a34e628e4", "paths": ["analysis/paper_posthoc/merra2_formula/B/rescore_B.py"]},
    {"entry": 209, "group": "Post hoc analysis code", "object": "merra2_formula/B/result_B.json", "value": "6dedad952413167a7f536a9790b950cf169cc25fe7fc804700a1322666902da1", "paths": ["analysis/paper_posthoc/merra2_formula/B/result_B.json"]},
    {"entry": 210, "group": "Post hoc analysis code", "object": "merra2_formula/reconcile/reconcile_AB.py", "value": "f3e4bfcbcdd94a9efe97304e92f8300f0cfbcef90fdd51872061ef364a8ed3a4", "paths": ["analysis/paper_posthoc/merra2_formula/reconcile/reconcile_AB.py"]},
    {"entry": 211, "group": "Post hoc analysis code", "object": "merra2_formula/reconcile/reconcile_AB.json", "value": "a29a7f6e9e0473df40725973ebf64353a12f91e0e99ce9c931ad961e3a8e9d67", "paths": ["analysis/paper_posthoc/merra2_formula/reconcile/reconcile_AB.json"]},
    {"entry": 212, "group": "Post hoc analysis code", "object": "v2_replay/SPEC.md", "value": "9e6743133d75e94b0d3bc4dd1debb5b20f31615fb2c6188d59189abb6ec8d00e", "paths": ["analysis/paper_posthoc/v2_replay/SPEC.md"]},
    {"entry": 213, "group": "Post hoc analysis code", "object": "v2_replay/INPUTS_SHA256.txt", "value": "90deaa81977de57867560234975a0725ae3c7a1124b226cb9a629ff16bb7ba79", "paths": ["analysis/paper_posthoc/v2_replay/INPUTS_SHA256.txt"]},
    {"entry": 214, "group": "Post hoc analysis code", "object": "v2_replay/A/replay_A.py", "value": "df5d0306879753fafb9c235fd006b9b9645fd39c616462ed5a860d11ceb41316", "paths": ["analysis/paper_posthoc/v2_replay/A/replay_A.py"]},
    {"entry": 215, "group": "Post hoc analysis code", "object": "v2_replay/A/result_A.json", "value": "3d04553cf50e19c57f40eab66c9d223fe1fd21e91c48da939111ad216167d7e5", "paths": ["analysis/paper_posthoc/v2_replay/A/result_A.json"]},
    {"entry": 216, "group": "Post hoc analysis code", "object": "v2_replay/B/replay_B.py", "value": "42a97b0fa9a8c47833d805e2fa44ef3aa86c352fa9819435a86953f5e9563924", "paths": ["analysis/paper_posthoc/v2_replay/B/replay_B.py"]},
    {"entry": 217, "group": "Post hoc analysis code", "object": "v2_replay/B/result_B.json", "value": "258f5c1f7b2a1b7d28452a98b28d07bde4980b773213a92f3a945211ba775a5f", "paths": ["analysis/paper_posthoc/v2_replay/B/result_B.json"]},
    {"entry": 218, "group": "Post hoc analysis code", "object": "v2_replay/reconcile/reconcile_AB.py", "value": "6f1fdd715354c377c6f3babc57f29af9cbd78d16b16faaa242287f3ff3fcd620", "paths": ["analysis/paper_posthoc/v2_replay/reconcile/reconcile_AB.py"]},
    {"entry": 219, "group": "Post hoc analysis code", "object": "v2_replay/reconcile/reconcile_AB.json", "value": "212dcce934d891641d8572c2203ed3f75c01dc263a78b4b3e4e7826ea60284ae", "paths": ["analysis/paper_posthoc/v2_replay/reconcile/reconcile_AB.json"]},
    {"entry": 220, "group": "Post hoc analysis code", "object": "v2_replay/{A,B}/rows_pm25_lead_0.parquet (identical)", "value": "75a95cc667c086159aff6bdf91c788dd3ea4b4f2e1a88ba607634776a3de98ec", "paths": ["analysis/paper_posthoc/v2_replay/A/rows_pm25_lead_0.parquet", "analysis/paper_posthoc/v2_replay/B/rows_pm25_lead_0.parquet", "analysis/paper_posthoc/v2_replay/A/tool_rerun/rows/pm25_20261007_74e67609_lead_0.parquet", "evidence/engine_v2/replay_af2_20261021/rows/pm25_20261007_74e67609_lead_0.parquet"]},
    {"entry": 221, "group": "Post hoc analysis code", "object": "v2_replay/{A,B}/rows_pm25_lead_6.parquet (identical)", "value": "8c550e1ac24b1e3fb207122a0ade547df3868a8b785abdc2f016e73e7f4b43da", "paths": ["analysis/paper_posthoc/v2_replay/A/rows_pm25_lead_6.parquet", "analysis/paper_posthoc/v2_replay/B/rows_pm25_lead_6.parquet"]},
    {"entry": 222, "group": "Post hoc analysis code", "object": "v2_replay/{A,B}/rows_pm25_lead_12.parquet (identical)", "value": "581c3109170d86256959d55e031e55e0ab82ee0e3ff72c8812238445516bb8bf", "paths": ["analysis/paper_posthoc/v2_replay/A/rows_pm25_lead_12.parquet", "analysis/paper_posthoc/v2_replay/B/rows_pm25_lead_12.parquet"]},
    {"entry": 223, "group": "Post hoc analysis code", "object": "v2_replay/{A,B}/rows_ndvi_lead_0.parquet (identical)", "value": "a27750f647271a1dfc4750a476ffdeeb5d9a2bc74bc35119174996c35d7349ab", "paths": ["analysis/paper_posthoc/v2_replay/A/rows_ndvi_lead_0.parquet", "analysis/paper_posthoc/v2_replay/B/rows_ndvi_lead_0.parquet", "analysis/paper_posthoc/v2_replay/A/tool_rerun/rows/ndvi_20261016_d1de3158_lead_0.parquet", "evidence/engine_v2/replay_af2_20261021/rows/ndvi_20261016_d1de3158_lead_0.parquet"]},
    {"entry": 224, "group": "Post hoc analysis code", "object": "v2_replay/{A,B}/rows_ndvi_lead_6.parquet (identical)", "value": "97fb271030b4460de60a4af78efb2b2b2c21122a4d1c5d71a333164d5c2245e8", "paths": ["analysis/paper_posthoc/v2_replay/A/rows_ndvi_lead_6.parquet", "analysis/paper_posthoc/v2_replay/B/rows_ndvi_lead_6.parquet"]},
    {"entry": 225, "group": "Post hoc analysis code", "object": "v2_replay/{A,B}/rows_ndvi_lead_12.parquet (identical)", "value": "841a98355af39c9cdb4486f0c3dcbb78987044f31b4d352d873fcee0a17bdd64", "paths": ["analysis/paper_posthoc/v2_replay/A/rows_ndvi_lead_12.parquet", "analysis/paper_posthoc/v2_replay/B/rows_ndvi_lead_12.parquet"]},
    {"entry": 226, "group": "Post hoc analysis code", "object": "v2_replay/{A,B}/rows_fire_lead_0.parquet (identical)", "value": "4d039974a9ed629fd51561840dfca8abd665c84c83bf7184a884291be7ee2e3e", "paths": ["analysis/paper_posthoc/v2_replay/A/rows_fire_lead_0.parquet", "analysis/paper_posthoc/v2_replay/B/rows_fire_lead_0.parquet", "analysis/paper_posthoc/v2_replay/A/tool_rerun/rows/fire_20261017_869d1f38_lead_0.parquet", "evidence/engine_v2/replay_af2_20261021/rows/fire_20261017_869d1f38_lead_0.parquet"]},
    {"entry": 227, "group": "Post hoc analysis code", "object": "v2_replay/{A,B}/rows_fire_lead_6.parquet (identical)", "value": "9807f74736eae58473534eee08bee96d07ea10a6f83a0cbc40aa3dec724180ba", "paths": ["analysis/paper_posthoc/v2_replay/A/rows_fire_lead_6.parquet", "analysis/paper_posthoc/v2_replay/B/rows_fire_lead_6.parquet"]},
    {"entry": 228, "group": "Post hoc analysis code", "object": "v2_replay/{A,B}/rows_fire_lead_12.parquet (identical)", "value": "9a878766ebd0aad7962938dcd28adae0ca8a77299a31cd2734204ae4bd92afa0", "paths": ["analysis/paper_posthoc/v2_replay/A/rows_fire_lead_12.parquet", "analysis/paper_posthoc/v2_replay/B/rows_fire_lead_12.parquet"]},
    {"entry": 229, "group": "Post hoc analysis code", "object": "v2_replay/{A,B}/rows_defo_lead_0.parquet (identical)", "value": "52c71652c52366acb820df8ce42af34456a66f7eb4ae4a1575aaf30fa18a7ea9", "paths": ["analysis/paper_posthoc/v2_replay/A/rows_defo_lead_0.parquet", "analysis/paper_posthoc/v2_replay/B/rows_defo_lead_0.parquet", "analysis/paper_posthoc/v2_replay/A/tool_rerun/rows/defo_20261017_d71c61f4_lead_0.parquet", "evidence/engine_v2/replay_af2_20261021/rows/defo_20261017_d71c61f4_lead_0.parquet"]},
    {"entry": 232, "group": "Coral bleaching 2017-2020 sensitivity row, Part 627", "object": "lock SENS_LOCK_PREPARED.json (written outside the lock tool)", "value": "d0d6bb851fc74bec2205dee7c8fdcc5c8d403a7dca7fa8892c92e1ecd9fba34b", "paths": ["analysis/coral_sens_2017_2020/SENS_LOCK_PREPARED.json"]},
    {"entry": 234, "group": "Coral bleaching 2017-2020 sensitivity row, Part 627", "object": "run/coral_sens_2017_2020/headline/20261029_75f66839/manifest.json", "value": "393e6c2e2da02cb396c5f0ecce2dea62768656087df859701142df7e89fabac9", "paths": ["analysis/coral_sens_2017_2020/run/coral_sens_2017_2020/headline/20261029_75f66839/manifest.json"]},
    {"entry": 236, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/bardl_shap.py", "value": "6bfc9aaf9548ec4b8c3115dca8837201967a4f350cf70dd5fe2f6d581d11a9a1", "paths": ["analysis/shap_v1/scripts/bardl_shap.py"]},
    {"entry": 237, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/compare_shap.py", "value": "918f099de461902cadd121dcb209ac45353c498eed9266af802ddefe4e56715f", "paths": ["analysis/shap_v1/scripts/compare_shap.py"]},
    {"entry": 238, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/make_sample.py", "value": "bf524989cf6a37135d1b58c3c60c14dccdf1ff2b52e85f1707f151b1f7ebbe41", "paths": ["analysis/shap_v1/scripts/make_sample.py"]},
    {"entry": 239, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/ridge_shap.py", "value": "866fd32931ab1da15223c94a10b7c0e47ac5c80ae75b7456a583e69573031c5c", "paths": ["analysis/shap_v1/scripts/ridge_shap.py"]},
    {"entry": 240, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/rival_shap.py", "value": "a3e836a51e8673012bca9ca26c67a2dac2630c467da0942519bb6ef94572d75e", "paths": ["analysis/shap_v1/scripts/rival_shap.py"]},
    {"entry": 241, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/run_shap.py", "value": "e99426f189c37385818817844553b1252a7fb0af046f8cec330eaa6f6d7c7170", "paths": ["analysis/shap_v1/scripts/run_shap.py"]},
    {"entry": 242, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/shapv1_common.py", "value": "85999624da8f1ba38d81453ddbfa1fed49af6843a61bc7d9cf719b31d2b9d812", "paths": ["analysis/shap_v1/scripts/shapv1_common.py"]},
    {"entry": 243, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/shapv1_rows.py", "value": "2e5fac9e8bf851af288cab81d7db400c2e658aa24f23fcbdbfebdfcc60a51a60", "paths": ["analysis/shap_v1/scripts/shapv1_rows.py"]},
    {"entry": 244, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/shapv1_stats.py", "value": "20f51cdee626df680d474e59dd84f428e3a1c45d1d6d5166603f1f7c5b2236b9", "paths": ["analysis/shap_v1/scripts/shapv1_stats.py"]},
    {"entry": 245, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/shapv1_treeshap.py", "value": "22a78b5c5a827cbc8afd5917688b1adffd08e169ed53c10b1390e400f981d961", "paths": ["analysis/shap_v1/scripts/shapv1_treeshap.py"]},
    {"entry": 246, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/tr_rebuild.py", "value": "b48196273b43ccc877249b00e16e2d4e11d3d09c83bad1eadd3ad200dc782beb", "paths": ["analysis/shap_v1/scripts/tr_rebuild.py"]},
    {"entry": 247, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/tr_shap.py", "value": "a38b6cb0fcde67ace21ca78ecb48e199ced2f15b8b40522bb1a0a7da27686055", "paths": ["analysis/shap_v1/scripts/tr_shap.py"]},
    {"entry": 248, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/tests/diag_coral_exactness.py", "value": "c8ab14c5e9484ebb3aa54b187d9720d36f57d0608f2651efcfc154aaf1074bda", "paths": ["analysis/shap_v1/scripts/tests/diag_coral_exactness.py"]},
    {"entry": 249, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/tests/smoke_bardl.py", "value": "0f7de758dbbaec4689ca38ab0108206aff7b4bb242184faa709a45dddf0a5b79", "paths": ["analysis/shap_v1/scripts/tests/smoke_bardl.py"]},
    {"entry": 250, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/tests/smoke_ridge.py", "value": "c48f3f66739103099a420cc93ef521be94b9312b7e1164522ee61d94fa36d545", "paths": ["analysis/shap_v1/scripts/tests/smoke_ridge.py"]},
    {"entry": 251, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/tests/smoke_unit.py", "value": "efdaf76bd3e7f27022e24f933704e19992e34de8bdfcf7fa0022cc743fcfb637", "paths": ["analysis/shap_v1/scripts/tests/smoke_unit.py"]},
    {"entry": 252, "group": "Post hoc SHAP comparison, Part 628: analysis scripts", "object": "scripts/tests/smoke_world.py", "value": "560068921cdeb209156cce419cd0059ca029c45f9f8ef7f886b2c115aab0ad8a", "paths": ["analysis/shap_v1/scripts/tests/smoke_world.py"]},
    {"entry": 253, "group": "Post hoc SHAP comparison, Part 628: the S3.13 table builders' scripts", "object": "A/scripts/build_tables.py", "value": "847791553e0451fe70ea3066180820aac1d38b2fda41b95fd32305e8986e4c5d", "paths": ["analysis/paper/supp_build/s3_13/A/scripts/build_tables.py"]},
    {"entry": 254, "group": "Post hoc SHAP comparison, Part 628: the S3.13 table builders' scripts", "object": "B/scripts/build_tables.py", "value": "26c82492b31e8f99a59317919776d8e03451df8274b00d5872f03ee77034c128", "paths": ["analysis/paper/supp_build/s3_13/B/scripts/build_tables.py"]},
]

# File hashes of Table S4.14 whose files are not archived, with the reason.
NOT_ARCHIVED = [
    {"entry": 230, "group": "Post hoc analysis code", "object": "v2_replay/{A,B}/rows_coral_lead_0.parquet (identical)", "value": "036f0c4f47c52d0ef2634ec4965d349c839e25c5ea878401dbde25bc2df4e7b6", "reason": "coral per-visit replay rows, kept out by ruling AT7; KEPT_OUT.md, section A"},
    {"entry": 231, "group": "Post hoc analysis code", "object": "v2_replay/{A,B}/rows_coral_lead_365.parquet (identical)", "value": "6683718798ee4b39a88a5c03ec9cae20450d4601ef8e63763870bef1fc643440", "reason": "coral per-visit replay rows, kept out by ruling AT7; KEPT_OUT.md, section A"},
    {"entry": 235, "group": "Coral bleaching 2017-2020 sensitivity row, Part 627", "object": "run/coral_sens_2017_2020/headline/20261029_75f66839/test_preds.parquet", "value": "26474c84991676abf7be0db5ee8b469c4ae51c91b26111435549b2f990705f62", "reason": "coral per-visit answers, kept out by ruling AT7; KEPT_OUT.md, section A"},
]

VERSION_BY_ID = dict((v['id'], v) for v in CODE_VERSIONS)


# --------------------------------------------------------------------------------------------- file listings
def sha256_file(path):
    """SHA-256 of a file's bytes, read in 1 MiB blocks."""
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        while True:
            block = fh.read(CHUNK)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def walk_files(root):
    """Every file under root as (relative path with '/' separators, full path)."""
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            path = os.path.join(dirpath, name)
            yield os.path.relpath(path, root).replace(os.sep, '/'), path


ENGINE_EXCLUDED = ('_proposed', '__pycache__')
REPORT_SUFFIXES = ('.py', '.yaml', '.yml')


def engine_paths(root):
    """{relative path: full path} of every .py file under treeroute/ except _proposed/ and __pycache__/
    (engine/treeroute/runs/fingerprint.py, engine_module_files)."""
    out = {}
    for rel, path in walk_files(root):
        parts = rel.split('/')
        if any(part in ENGINE_EXCLUDED for part in parts):
            continue
        if parts[-1].lower().endswith('.py'):
            out[rel] = path
    return out


def list_engine(root):
    return {rel: sha256_file(path) for rel, path in engine_paths(root).items()}


def list_report(root):
    """{relative path: SHA-256} of every .py, .yaml and .yml file under treeroute_report/ outside __pycache__/
    (engine/treeroute_report/common.py, report_file_hashes)."""
    out = {}
    for rel, path in walk_files(root):
        parts = rel.split('/')
        if '__pycache__' in parts:
            continue
        if os.path.splitext(parts[-1])[1].lower() in REPORT_SUFFIXES:
            out[rel] = sha256_file(path)
    return out


def top_py(folder):
    return [name for name in os.listdir(folder)
            if name.lower().endswith('.py') and os.path.isfile(os.path.join(folder, name))]


def list_harness(root):
    """{file name: SHA-256} of rivals/*.py; the tests sit in a sub-folder, outside the hash
    (rivals_code/rivals_build/rivals/harness.py, harness_code_sha)."""
    return {name: sha256_file(os.path.join(root, name)) for name in top_py(root)}


def list_export(root):
    """export.py and layout.py (rivals_code/rivals_build/rivals/export.py, code_sha)."""
    return {name: sha256_file(os.path.join(root, name)) for name in ('export.py', 'layout.py')}


def list_tool(root):
    """{'rivals_human/<name>' or 'adapters/<name>': SHA-256} of rivals_human/*.py and adapters/*.py
    (rivals_code/human_rivals_build/human/rivals_human/config.py, code_files)."""
    out = {}
    for folder in ('rivals_human', 'adapters'):
        d = os.path.join(root, folder)
        for name in top_py(d):
            out[folder + '/' + name] = sha256_file(os.path.join(d, name))
    return out


# --------------------------------------------------------------------------------------------- recipes
def canonical(obj):
    """The canonical JSON the code hashes are taken of: sorted keys, no spaces, ASCII only."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False, ensure_ascii=True)


def sha256_text(text):
    return hashlib.sha256(text.encode('ascii')).hexdigest()


def windows_order(names):
    """The order of sorted(Path.glob('*.py')) on Windows, where these hashes were formed: Windows paths compare by
    their lower-cased parts. PureWindowsPath gives that order on any system (a case-insensitive sort by another
    rule, which may place '_' elsewhere, gives a different hash)."""
    return sorted(names, key=PureWindowsPath)


def hash_engine(files):
    """engine_code_sha256: the canonical JSON of the [relative path, SHA-256] list, sorted by the relative path
    as a Python string (fingerprint.py)."""
    return sha256_text(canonical([[rel, files[rel]] for rel in sorted(files)]))


def hash_report(files):
    """report_tooling_sha256: json.dumps of the sorted (relative path, SHA-256) pairs (treeroute_report/freeze.py)."""
    return hashlib.sha256(json.dumps(sorted(files.items()), separators=(',', ':')).encode('utf-8')).hexdigest()


def hash_harness(files):
    """harness_code_sha: the canonical JSON of [file name, SHA-256] in Windows path order."""
    return sha256_text(canonical([[name, files[name]] for name in windows_order(files)]))


def hash_export(files):
    """code_sha of the export code: [file name, SHA-256] of export.py, then layout.py (layout.py, code_sha)."""
    return sha256_text(canonical([['export.py', files['export.py']], ['layout.py', files['layout.py']]]))


def hash_tool(files):
    """tool_code_sha: [folder/name, SHA-256] of rivals_human/*.py, then adapters/*.py, each in Windows path order
    (rivals_code/human_rivals_build/human/rivals_human/common.py)."""
    parts = []
    for folder in ('rivals_human', 'adapters'):
        names = [key.split('/', 1)[1] for key in files if key.split('/', 1)[0] == folder]
        parts += [[folder + '/' + name, files[folder + '/' + name]] for name in windows_order(names)]
    if len(parts) != len(files):
        raise ValueError('a tool file is outside rivals_human/ and adapters/')
    return sha256_text(json.dumps(parts, sort_keys=True, separators=(',', ':'), ensure_ascii=True))


LISTERS = {'engine': list_engine, 'report': list_report, 'harness': list_harness, 'export': list_export,
           'tool': list_tool}
HASHERS = {'engine': hash_engine, 'report': hash_report, 'harness': hash_harness, 'export': hash_export,
           'tool': hash_tool}

SKIP_TOKENS = (tokenize.COMMENT, tokenize.NL, tokenize.ENCODING)


def code_hash(source):
    """fingerprint.py code_hash: the canonical JSON of the [token name, token text] stream without comments,
    blank lines and the encoding token."""
    tokens = []
    for tok in tokenize.tokenize(io.BytesIO(source).readline):
        if tok.type in SKIP_TOKENS:
            continue
        tokens.append([tokenize.tok_name[tok.type], tok.string])
    return sha256_text(canonical(tokens))


def hash_stripped(root):
    """engine_code_hash: the canonical JSON of {relative path: code_hash} over the engine files."""
    hashes = {}
    for rel, path in engine_paths(root).items():
        with open(path, 'rb') as fh:
            hashes[rel] = code_hash(fh.read())
    return sha256_text(canonical(hashes))


CONSTANTS_CODE = (
    'import json, sys\n'
    'sys.path.insert(0, sys.argv[1])\n'
    'from treeroute import engine_constants\n'
    'print(json.dumps({"hash": engine_constants.constants_hash(), "file": engine_constants.__file__}))\n')


def hash_constants(folder):
    """constants_hash() of the version's own treeroute/engine_constants.py, in a separate process (-I: no user
    site and no current folder on the path; -B: no bytecode written)."""
    run = subprocess.run([sys.executable, '-I', '-B', '-c', CONSTANTS_CODE, folder], capture_output=True, text=True)
    if run.returncode != 0:
        lines = run.stderr.strip().splitlines()
        raise RuntimeError(lines[-1] if lines else 'exit code %d' % run.returncode)
    out = json.loads(run.stdout.strip().splitlines()[-1])
    expected = os.path.join(folder, 'treeroute', 'engine_constants.py')
    if not os.path.samefile(out['file'], expected):
        raise RuntimeError('engine_constants.py was not read from the version folder')
    return out['hash']


# --------------------------------------------------------------------------------------------- report lines
class Tally(object):
    def __init__(self):
        self.counts = {}
        self.failures = []

    def add(self, section, status, line):
        self.counts.setdefault(section, {}).setdefault(status, 0)
        self.counts[section][status] += 1
        print('%-13s %s' % (status, line))
        if status == 'FAIL':
            self.failures.append(line)

    @staticmethod
    def more(line):
        print('%-13s %s' % ('', line))


def overlay_rebuild(vid, spec, listings, rebuilt, root, tally):
    """Rebuilds an overlay version in memory from archived parts and checks it."""
    base_id = spec['base']
    if base_id in OVERLAYS:
        if base_id not in rebuilt:
            raise RuntimeError('its base %s could not be rebuilt' % base_id)
        files = dict(rebuilt[base_id])
        base_text = '%s as rebuilt above' % base_id
    else:
        if base_id not in listings:
            raise RuntimeError('its base %s could not be read' % base_id)
        files = dict(listings[base_id])
        base_text = '%s (%s/)' % (base_id, VERSION_BY_ID[base_id]['folder'])
    steps = []
    for step in spec['steps']:
        if step[0] == 'put back folder':
            folder, n = step[1], step[2]
            part = {}
            for rel, path in walk_files(os.path.join(root, *folder.split('/'))):
                part[rel] = sha256_file(path)
            if len(part) != n:
                raise RuntimeError('%s holds %d files, not %d' % (folder, len(part), n))
            files.update(part)
            steps.append('put back the %d files of %s/' % (n, folder))
        elif step[0] == 'put back files':
            for rel, src in sorted(step[1].items()):
                files[rel] = sha256_file(os.path.join(root, *src.split('/')))
                steps.append('put back %s from %s' % (rel, src))
        elif step[0] == 'remove':
            for rel in step[1]:
                if rel not in files:
                    raise RuntimeError('%s is not in the version to remove it from' % rel)
                del files[rel]
            steps.append('removed %d files (%s)' % (len(step[1]), ', '.join(step[1])))
        else:
            raise RuntimeError('unknown step %r' % (step[0],))
    rebuilt[vid] = files
    v = VERSION_BY_ID[vid]
    got = HASHERS[v['recipe']](files)
    same = files == listings.get(vid)
    text = '%s  from %s: %s; %d files; %s; %s' % (
        vid, base_text, '; '.join(steps), len(files), got,
        'same files as the written-out folder' if same else 'NOT the files of the written-out folder')
    if got != v['value']:
        text += '  (Table S4.14: %s)' % v['value']
    tally.add('1b overlay rebuilds', 'PASS' if (got == v['value'] and same) else 'FAIL', text)


def check_code_versions(root, tally):
    print('')
    print('1. Code versions (VERSIONS.md; Table S4.14 entries in brackets)')
    listings = {}
    for v in CODE_VERSIONS:
        folder = os.path.join(root, *v['folder'].split('/'))
        label = '%s  %s, %s: %s/  [%s]' % (v['id'], v['title'], v['how'], v['folder'],
                                          ', '.join('#%d' % n for n in v['entries']))
        if not os.path.isdir(folder):
            tally.add('1 code versions', 'FAIL', label + '  folder missing')
            continue
        try:
            files = LISTERS[v['recipe']](folder)
            got = HASHERS[v['recipe']](files)
        except (OSError, ValueError, KeyError) as exc:
            tally.add('1 code versions', 'FAIL', '%s  %s' % (label, exc))
            continue
        listings[v['id']] = files
        status = 'PASS' if got == v['value'] else 'FAIL'
        tally.add('1 code versions', status, '%s  %d files  %s%s' % (
            label, len(files), got, '' if status == 'PASS' else '  (Table S4.14: %s)' % v['value']))
    print('')
    print('1b. Overlay versions rebuilt in memory from the archived parts that VERSIONS.md names')
    rebuilt = {}
    for vid in OVERLAY_ORDER:
        try:
            if vid not in listings:
                raise RuntimeError('its written-out folder could not be read')
            overlay_rebuild(vid, OVERLAYS[vid], listings, rebuilt, root, tally)
        except (OSError, RuntimeError, KeyError) as exc:
            tally.add('1b overlay rebuilds', 'FAIL', '%s  rebuild failed: %s' % (vid, exc))


def check_stripped_and_constants(root, tally):
    print('')
    print('2. Comment-stripped engine code and engine constants of the locked treeroute v1 versions')
    py39 = sys.version_info[:2] == (3, 9)
    for s in STRIPPED:
        label = '#%d  comment-stripped engine code of %s: %s/' % (s['entry'], s['id'], s['folder'])
        try:
            got = hash_stripped(os.path.join(root, *s['folder'].split('/')))
        except (OSError, SyntaxError, tokenize.TokenError) as exc:
            tally.add('2 stripped code', 'FAIL', '%s  %s' % (label, exc))
            continue
        if got == s['value']:
            tally.add('2 stripped code', 'PASS', '%s  %s' % (label, got))
        elif not py39:
            tally.add('2 stripped code', 'NOT CHECKED', '%s  needs Python 3.9 (this is %s)' % (
                label, '.'.join(map(str, sys.version_info[:3]))))
        else:
            tally.add('2 stripped code', 'FAIL', '%s  %s  (Table S4.14: %s)' % (label, got, s['value']))
    for c in CONSTANTS:
        label = '#%d  engine constants of %s: %s/treeroute/engine_constants.py' % (c['entry'], c['id'], c['folder'])
        try:
            got = hash_constants(os.path.join(root, *c['folder'].split('/')))
        except (OSError, RuntimeError, ValueError) as exc:
            tally.add('2 engine constants', 'FAIL', '%s  %s' % (label, exc))
            continue
        tally.add('2 engine constants', 'PASS' if got == c['value'] else 'FAIL', '%s  %s%s' % (
            label, got, '' if got == c['value'] else '  (Table S4.14: %s)' % c['value']))


def check_files(root, tally):
    print('')
    print('3. File hashes of Table S4.14 (HASH_REGISTER.md)')
    copies = 0
    for f in FILES:
        label = '#%d  %s: %s' % (f['entry'], f['group'], f['object'])
        bad = []
        for i, p in enumerate(f['paths']):
            path = os.path.join(root, *p.split('/'))
            if not os.path.isfile(path):
                bad.append('missing: %s' % p)
                continue
            got = sha256_file(path)
            if got != f['value']:
                bad.append('%s has %s' % (p, got))
            elif i:
                copies += 1
        if bad:
            tally.add('3 files', 'FAIL', '%s  %s  expected %s; %s' % (label, f['paths'][0], f['value'], '; '.join(bad)))
        else:
            tally.add('3 files', 'PASS', '%s  %s  %s' % (label, f['paths'][0], f['value']))
        for p in f['paths'][1:]:
            tally.more('identical copy: %s' % p)
    for f in NOT_ARCHIVED:
        tally.add('3 files', 'NOT ARCHIVED', '#%d  %s: %s  %s' % (f['entry'], f['group'], f['object'], f['value']))
        tally.more('not archived: %s' % f['reason'])
    return copies


REG_ROW = re.compile(r'^\|\s*(\d+)\s*\|.*?\|\s*([a-z ]+?)\s*\|\s*`([0-9a-f]{64})`\s*\|')


def check_documents(docs, tally):
    print('')
    print('4. Agreement with HASH_REGISTER.md and VERSIONS.md')
    want = {}
    for v in CODE_VERSIONS:
        for n in v['entries']:
            want[n] = v['value']
    for s in STRIPPED + CONSTANTS + FILES + NOT_ARCHIVED:
        want[s['entry']] = s['value']
    reg = os.path.join(docs, 'HASH_REGISTER.md')
    if os.path.isfile(reg):
        rows = {}
        with open(reg, encoding='utf-8') as fh:
            for line in fh:
                m = REG_ROW.match(line)
                if m:
                    rows[int(m.group(1))] = (m.group(2), m.group(3))
        differ = sorted(n for n in want if n not in rows or rows[n][1] != want[n])
        uncovered = sorted(n for n, (kind, value) in rows.items()
                           if n not in want and kind in ('file', 'engine code', 'stripped code'))
        tally.add('4 documents', 'PASS' if not differ else 'FAIL', 'HASH_REGISTER.md: %d rows read; the %d entries '
                  'checked here give the same values%s' % (len(rows), len(want), '' if not differ else
                                                            ', except #' + ', #'.join(map(str, differ))))
        tally.add('4 documents', 'PASS' if not uncovered else 'FAIL', 'HASH_REGISTER.md: every file and engine-code '
                  'entry is checked here%s' % ('' if not uncovered else ', except #' + ', #'.join(map(str, uncovered))))
    else:
        tally.add('4 documents', 'NOT CHECKED', 'HASH_REGISTER.md is not in %s' % docs)
    ver = os.path.join(docs, 'VERSIONS.md')
    if os.path.isfile(ver):
        with open(ver, encoding='utf-8') as fh:
            text = fh.read()
        missing = [v['id'] for v in CODE_VERSIONS if v['value'] not in text]
        tally.add('4 documents', 'PASS' if not missing else 'FAIL', 'VERSIONS.md: the full hash of each of the %d '
                  'code versions is in it%s' % (len(CODE_VERSIONS), '' if not missing else ', except ' +
                                                ', '.join(missing)))
    else:
        tally.add('4 documents', 'NOT CHECKED', 'VERSIONS.md is not in %s' % docs)


def main(argv):
    args = list(argv)
    docs = None
    if '--docs' in args:
        i = args.index('--docs')
        if i + 1 >= len(args):
            print('usage: VERIFY_HASHES.py [archive folder] [--docs folder]')
            return 2
        docs = args[i + 1]
        del args[i:i + 2]
    if len(args) > 1:
        print('usage: VERIFY_HASHES.py [archive folder] [--docs folder]')
        return 2
    root = os.path.abspath(args[0] if args else os.path.dirname(os.path.abspath(__file__)))
    docs = os.path.abspath(docs) if docs else root
    print('VERIFY_HASHES.py: code hashes (VERSIONS.md) and file hashes of Table S4.14 (HASH_REGISTER.md)')
    print('archive folder: %s' % root)
    if docs != root:
        print('documents read from: %s' % docs)
    print('Python %s (%s)' % (sys.version.split()[0], sys.implementation.name))
    if not os.path.isdir(root):
        print('FAIL: the archive folder does not exist')
        return 1
    tally = Tally()
    check_code_versions(root, tally)
    check_stripped_and_constants(root, tally)
    copies = check_files(root, tally)
    check_documents(docs, tally)
    print('')
    print('Summary')
    for section in sorted(tally.counts):
        c = tally.counts[section]
        print('  %-22s %s' % (section, ', '.join('%s %d' % (k, c[k]) for k in sorted(c))))
    print('  identical copies checked beside their files: %d' % copies)
    if tally.failures:
        print('RESULT: %d check(s) FAILED' % len(tally.failures))
        return 1
    print('RESULT: every check passed')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
