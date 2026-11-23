# -*- coding: utf-8 -*-
# Negative control (prints only; writes nothing): runs the version-4 verify_constants.py, unchanged except that it
# reads the version-3 build script (scripts\v3\build_tables.py) in place of build_tables.py, against the version-4
# spec. Every text that version 4 changed should be reported (none of them is a version-4 spec text), so the
# 0 problems of the real run are not vacuous.
# Run as: py -3.9 -I -B <this script>
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
VC = os.path.join(HERE, "verify_constants.py")
with open(VC, "r", encoding="utf-8") as f:
    src = f.read()
old = 'os.path.join(HERE, "build_tables.py")'
if src.count(old) != 2:
    print("STOP: the build script path is not found twice in verify_constants.py")
    sys.exit(1)
src = src.replace(old, 'os.path.join(HERE, "v3", "build_tables.py")')
g = {"__name__": "vc_on_v3", "__file__": VC}
exec(compile(src, VC + " (reading v3\\build_tables.py)", "exec"), g)
