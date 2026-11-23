# r19 (version 3): before any version-2 script of the reconciler is updated, keep byte copies of the four whose input
# version 3 changes (r02: the S3.18 a guard text, the S3.22 row label and the Link cell words; r04: the constant texts
# that it re-derives; r06: two fenced blocks found by their first line and the {extra_src} value; r15: TABLE_SPEC.md and
# tables.md are now version 3) in OUT\reconcile\scripts\v2\, and print the SHA-256 of each original and copy. The
# copies are records, not to be run from that folder (their paths are found from their own place). Stops if a copy
# exists already. scripts\v1\ is not touched.
import sys, hashlib
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
dst = HERE / "v2"
names = ("r02_official_compare.py", "r04_rebuild_bodies.py", "r06_rebuild_document.py", "r15_note344_tokens.py")
for name in names:
    if (dst / name).exists():
        raise SystemExit("stop: scripts\\v2\\%s exists already" % name)
dst.mkdir(exist_ok=True)
for name in names:
    b = (HERE / name).read_bytes()
    with open(dst / name, "xb") as fh:
        fh.write(b)
    print("%-26s %6d bytes, sha256 %s ; copy equal: %s" % (name, len(b), hashlib.sha256(b).hexdigest(), (dst / name).read_bytes() == b))
