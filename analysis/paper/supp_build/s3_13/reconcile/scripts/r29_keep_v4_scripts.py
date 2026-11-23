# r29 (version 5): before any version-4 script of the reconciler is updated, keep byte copies of the three whose input
# version 5 changes (r04: the "What it checks" texts of S3.21's E3m, V5-4, and E5, V5-3, which it re-derives; r15:
# TABLE_SPEC.md, OUT\A\tables.md and OUT\A\cells.json now hold version 5, and version 4 is now in TABLE_SPEC_v4.md,
# OUT\reconcile\tables_agreed_v4.md and OUT\reconcile\cells_v4.json; r16: the copies made here are added to its list)
# in OUT\reconcile\scripts\v4\, and print the SHA-256 of each original and copy. The copies are records, not to be run
# from that folder (their paths are found from their own place). Stops if a copy exists already. scripts\v1\ to
# scripts\v3\ are not touched. r06 (the blocks that version 5 changed keep the starts by which it finds them) and the
# other scripts are not changed, so they are not copied.
import sys, hashlib
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
dst = HERE / "v4"
names = ("r04_rebuild_bodies.py", "r15_note344_tokens.py", "r16_compile_check.py")
for name in names:
    if (dst / name).exists():
        raise SystemExit("stop: scripts\\v4\\%s exists already" % name)
dst.mkdir(exist_ok=True)
for name in names:
    b = (HERE / name).read_bytes()
    with open(dst / name, "xb") as fh:
        fh.write(b)
    print("%-26s %6d bytes, sha256 %s ; copy equal: %s" % (name, len(b), hashlib.sha256(b).hexdigest(), (dst / name).read_bytes() == b))
