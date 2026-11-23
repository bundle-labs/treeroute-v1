"""The run manifest (plan 7.1): written once, atomically, at the start of a run.

It records what makes a run reproducible: the engine module hashes (comments stripped), the engine
constants (id, value, test-exposed flag, status; ids only, no names), library and Python versions,
every thread pool from the launch record, the backend state, the GLS forest seed, the package
fingerprint, the resolved config, the machine-file paths and argv. Items whose producing module is
not built yet are recorded as null and listed under ``not_built_yet``.
"""

import datetime
import hashlib
import platform
import sys
from pathlib import Path

import treeroute
from treeroute import engine_constants as K
from treeroute.runs.atomic import dumps_canonical, write_json_once
from treeroute.runs.fingerprint import (assert_no_proposed_code_loaded, engine_code_hash,
                                        engine_code_hashes, library_versions,
                                        loaded_engine_modules)

MANIFEST_FILE = "manifest.json"


def _hash_or_none(obj):
    if obj is None:
        return None
    return hashlib.sha256(dumps_canonical(obj).encode("ascii")).hexdigest()


def build_manifest(fingerprint, package_fingerprint, machine_record, config=None,
                   launch_record=None, feature_list=None, unit_list_hashes=None,
                   table_schedule=None, lock_file_hash=None, argv=None):
    """Assemble the manifest dict. ``launch_record`` defaults to the launcher's record, which
    refuses if the engine was not started through treeroute.launch. Refuses while any proposed
    (unsigned, unhashed) module from treeroute/_proposed/ is loaded."""
    assert_no_proposed_code_loaded()
    if launch_record is None:
        from treeroute import launch

        launch_record = launch.record()
    manifest = {
        "fingerprint": fingerprint,
        "engine_version": treeroute.__version__,
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "engine_modules": engine_code_hashes(),
        "engine_code_hash": engine_code_hash(),
        "loaded_engine_modules": loaded_engine_modules(),
        "engine_constants": K.table(),
        "engine_constants_hash": K.constants_hash(),
        "versions": library_versions(),
        "python": platform.python_version(),
        "launch": launch_record,
        "gls_random_state": K.GLS_RANDOM_STATE,
        "package_fingerprint": package_fingerprint,
        "config": config,
        "feature_list": feature_list,
        "feature_list_hash": _hash_or_none(feature_list),
        "unit_list_hashes": unit_list_hashes,
        "table_schedule": table_schedule,
        "lock_file_hash": lock_file_hash,
        "machine": machine_record,
        "argv": list(sys.argv if argv is None else argv),
    }
    optional = ("config", "feature_list", "unit_list_hashes", "table_schedule", "lock_file_hash")
    manifest["not_built_yet"] = [k for k in optional if manifest[k] is None]
    return manifest


def write_manifest(run_dir, manifest):
    """Write manifest.json once; an existing manifest is refused."""
    path = Path(run_dir) / MANIFEST_FILE
    write_json_once(path, manifest)
    return path
