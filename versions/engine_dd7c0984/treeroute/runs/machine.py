"""The machine file: config/machine.yaml at the engine repo root, OUTSIDE treeroute/.

It holds paths only (run root, temp dir, registry dir). It is outside the engine hash and outside
the G-NONAMES scan; its paths are recorded in each manifest. Thread counts are engine constants and
may not appear here (the schema forbids any other key).
"""

import os
from pathlib import Path

from pydantic import ValidationError

from treeroute.errors import PackageError
from treeroute.package.load import load_yaml
from treeroute.package.schema import MachineFile

# engine/treeroute/runs/machine.py -> engine/config/machine.yaml
MACHINE_FILE = Path(__file__).resolve().parents[2] / "config" / "machine.yaml"


def load_machine(path=None):
    """Load and validate the machine file. Every path must be absolute."""
    path = Path(path) if path is not None else MACHINE_FILE
    if not path.is_file():
        raise PackageError("machine file %s is missing" % path)
    data = load_yaml(path)
    try:
        machine = MachineFile.model_validate(data)
    except ValidationError as exc:
        raise PackageError("machine file %s is invalid:\n%s" % (path, exc)) from exc
    for field in ("run_root", "temp_dir", "registry_dir"):
        value = getattr(machine, field)
        if not os.path.isabs(value):
            raise PackageError("machine file %s: %s must be an absolute path, got %r"
                               % (path, field, value))
    return machine


def machine_record(machine, path=None):
    """What the manifest records about the machine file."""
    return {"file": str(Path(path) if path is not None else MACHINE_FILE),
            "run_root": machine.run_root, "temp_dir": machine.temp_dir,
            "registry_dir": machine.registry_dir}
