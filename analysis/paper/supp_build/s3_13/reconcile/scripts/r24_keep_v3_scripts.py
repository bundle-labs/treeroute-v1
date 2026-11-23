# r24 (version 4): before any version-3 script of the reconciler is updated, keep byte copies of the five whose input
# version 4 changes (r02: the S3.22 row label of the cross-link rivals, V4-8; r04: the constant texts that it
# re-derives, V4-1, V4-2, V4-5, V4-6, V4-8, V4-10, V4-11; r06: block 15 of the spec, found by its first line, V4-7;
# r15: TABLE_SPEC.md, OUT\A\tables.md and OUT\A\cells.json now hold version 4; r16: the copies made here are added to
# its list) in OUT\reconcile\scripts\v3\, and print the SHA-256 of each original and copy. The copies are records, not
# to be run from that folder (their paths are found from their own place). Stops if a copy exists already.
# scripts\v1\ and scripts\v2\ are not touched.
import sys, hashlib
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
dst = HERE / "v3"
names = ("r02_official_compare.py", "r04_rebuild_bodies.py", "r06_rebuild_document.py", "r15_note344_tokens.py", "r16_compile_check.py")
for name in names:
    if (dst / name).exists():
        raise SystemExit("stop: scripts\\v3\\%s exists already" % name)
dst.mkdir(exist_ok=True)
for name in names:
    b = (HERE / name).read_bytes()
    with open(dst / name, "xb") as fh:
        fh.write(b)
    print("%-26s %6d bytes, sha256 %s ; copy equal: %s" % (name, len(b), hashlib.sha256(b).hexdigest(), (dst / name).read_bytes() == b))
