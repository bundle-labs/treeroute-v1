# r10b (version 2): before any version-1 script of the reconciler is updated, keep byte copies of the three that
# version 2 changes the input of (r02, r04, r06) in OUT\reconcile\scripts\v1\, and print the SHA-256 of each
# original and copy. r09 (the version-1 writer) is not copied: its privacy scan holds a user-name fragment in a
# regex, which version 2 removes; only its SHA-256 is printed. The copies are records, not to be run from that
# folder (their paths are found from their own place). Stops if a copy exists already.
import sys, hashlib, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
dst = HERE / "v1"
dst.mkdir(exist_ok=True)
for name in ("r02_official_compare.py", "r04_rebuild_bodies.py", "r06_rebuild_document.py"):
    src = HERE / name
    out = dst / name
    if out.exists():
        raise SystemExit("stop: scripts\\v1\\%s exists already" % name)
    b = src.read_bytes()
    with open(out, "xb") as fh:
        fh.write(b)
    print(name, len(b), "bytes, sha256", hashlib.sha256(b).hexdigest(), "; copy equal:", out.read_bytes() == b)
b = (HERE / "r09_write_agreed.py").read_bytes()
print("r09_write_agreed.py (version 1, not copied)", len(b), "bytes, sha256", hashlib.sha256(b).hexdigest())
