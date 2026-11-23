# r16 (version 2): every script of OUT\reconcile\scripts (and the version-1 copies in scripts\v1) compiles
# (Python's compile(), nothing is executed or written), and the SHA-256 of each is printed for the record.
# Version 3 (2026-11-17): the version-2 copies in scripts\v2 (r19) are included; nothing else changed.
# Version 4 (2026-11-17): the version-3 copies in scripts\v3 (r24) are included; nothing else changed. Version 3 is
# kept as scripts\v3\r16_compile_check.py.
# Version 5 (2026-11-17): the version-4 copies in scripts\v4 (r29) are included; nothing else changed. Version 4 is
# kept as scripts\v4\r16_compile_check.py.
import sys, hashlib
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
for f in sorted(HERE.glob("*.py")) + sorted((HERE / "v1").glob("*.py")) + sorted((HERE / "v2").glob("*.py")) + sorted((HERE / "v3").glob("*.py")) + sorted((HERE / "v4").glob("*.py")):
    b = f.read_bytes()
    compile(b.decode("utf-8"), f.name, "exec")
    print("%-28s %6d bytes  sha256 %s  compiles" % (str(f.relative_to(HERE)), len(b), hashlib.sha256(b).hexdigest()))
