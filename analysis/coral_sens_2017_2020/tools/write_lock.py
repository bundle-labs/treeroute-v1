"""Write SENS_LOCK_PREPARED.json: the hashes the declared short Part pins before the run (builder hash, package
fingerprint, engine hash; engine/PREREGISTRATION_DRAFT_coral.md 4.2). A lock written OUTSIDE the freeze tool (the
freeze refuses a DRAFT package, F-DRAFT); it binds only when the owner signs Part 627. Read only except its output.

    py -3.9 -I -B write_lock.py
"""
import datetime as dt
import hashlib
import json
import os
import sys

sys.dont_write_bytecode = True
ENGINE = r"C:\Users\moh the ghost\Desktop\data set for reserch paper\engine"
sys.path.insert(0, ENGINE)
from treeroute.package.load import load_package  # noqa: E402
from treeroute.runs.fingerprint import engine_code_hash, engine_code_sha256  # noqa: E402

S = r"D:\treeroute\analysis\coral_sens_2017_2020"
ROOT = r"C:\Users\moh the ghost\Desktop\data set for reserch paper"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def tree(folder):
    out = {}
    for dp, dn, fn in os.walk(folder):
        dn[:] = sorted(d for d in dn if d != "__pycache__")
        for n in sorted(fn):
            p = os.path.join(dp, n)
            out[os.path.relpath(p, folder).replace("\\", "/")] = sha(p)
    return out


pkg = load_package(os.path.join(S, "package", "coral_sens_2017_2020"))
lock = {
    "what": "coral 2017-2020 sensitivity row (declared by ruling V3; run under ruling AN3) -- PREPARED, not run",
    "written_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "binds_when": "the owner signs PENDING_PARTS Part 627 (lock written outside the freeze tool; F-DRAFT refuses a "
                  "DRAFT package in treeroute_report.freeze)",
    "engine": {"engine_code_sha256": engine_code_sha256(), "engine_code_hash": engine_code_hash(),
               "headline_run_engine_code_hash": "85c64b55c02e638cfcb7cefb0fe92af4870d4faed5c21e3f46bbdcbcd0e3a678",
               "install_engine_code_sha256": "930d961cdfdd219c36b113174e6c865096f973068e30696850f13d5ec4a60814"},
    "package": {"path": os.path.join(S, "package", "coral_sens_2017_2020"), "name": pkg.dataset.name,
                "fingerprint": pkg.fingerprint, "files": tree(os.path.join(S, "package", "coral_sens_2017_2020")),
                "headline_package_fingerprint": "5b9383f0446df0f12e460cccb2bcd2e58d09fbf22b234cf2943a07aac14644c9"},
    "builder_copy": tree(os.path.join(S, "builder")),
    "builder_originals": {
        "D:/treeroute/coral_build/coral_tables/build_visits.py": sha(r"D:\treeroute\coral_build\coral_tables\build_visits.py"),
        "D:/treeroute/coral_build/coral_tables/build_tables.py": sha(r"D:\treeroute\coral_build\coral_tables\build_tables.py"),
        "D:/treeroute/coral_build/coral_tables/check_tables.py": sha(r"D:\treeroute\coral_build\coral_tables\check_tables.py"),
        "D:/treeroute/coral_build/coral_tables/columns.py": sha(r"D:\treeroute\coral_build\coral_tables\columns.py"),
        "D:/treeroute/coral_build/coral_tables/npz_map.py": sha(r"D:\treeroute\coral_build\coral_tables\npz_map.py"),
        "D:/treeroute/coral_build_v6b/coral_tables/make_split.py": sha(r"D:\treeroute\coral_build_v6b\coral_tables\make_split.py")},
    "builder_imports_project_root": {n: sha(os.path.join(ROOT, n)) for n in
                                     ("coral_safe.py", "coral_mhw_features.py", "coral_extra_drivers.py")},
    "stage1_outputs": {n: sha(os.path.join(S, "coral_data", n)) for n in
                       ("visits.parquet", "visits_census.json", "month_precision_rows.csv")},
    "tools": tree(os.path.join(S, "tools")),
    "expected_after_stage2": {
        "rows": {"lead_0": 13723, "lead_183": 13715, "lead_365": 13715},
        "marks_lead_0": {"train": 12230, "test": 1493},
        "check": "tools/compare_features.py coral_data/full -> RESULT: PASS (every headline row bit-identical except "
                 "mark; mark differs only for 2016 visits; extra rows only of 2020)",
        "preview_plan_derived_sha256": "574d080559cee060db11c8d8ad2cdae5202b68d94398cababdb5a5e6b3c4a5f9",
        "preview_plan_content_sha256": "ee0c7e46e5026b85cfde50f2b98d04369f1ae4b542f33aef0d105e4d816635ed"},
    "expected_windows": {"R3": 2020, "R4": 1994, "R5": [2017, 2018, 2019, 2020], "R6": 2016,
                         "R7": {"inner_fit": [1994, 2013], "inner_score": [2014, 2015, 2016]},
                         "R11_cuts": {"0": ["2016-12-31", "2013-12-31"], "183": ["2016-07-02", "2013-07-02"],
                                      "365": ["2016-01-02", "2013-01-01"]}},
    "run_root": os.path.join(S, "run"),
}
out = os.path.join(S, "SENS_LOCK_PREPARED.json")
with open(out, "w", encoding="utf-8", newline="\n") as f:
    json.dump(lock, f, indent=1, sort_keys=False)
print("wrote %s" % out)
print("package fingerprint %s | engine_code_sha256 %s | engine_code_hash %s"
      % (pkg.fingerprint, lock["engine"]["engine_code_sha256"], lock["engine"]["engine_code_hash"]))
print("SHA-256 of the lock file: %s" % sha(out))
