# -*- coding: utf-8 -*-
# Negative control (prints only; writes nothing): runs verify_constants.py (unchanged in version 5), except that it
# reads the version-4 build script (scripts\v4\build_tables.py) in place of build_tables.py, against the version-5
# spec. Each of the six constants that version 5 changed (the header comment, the Table 9 caption, S3.19 note c,
# S3.21 note a and the "What it checks" cells of E3m and E5) should be reported, and nothing else, so the 0 problems
# of the real run are not vacuous.
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
src = src.replace(old, 'os.path.join(HERE, "v4", "build_tables.py")')
g = {"__name__": "vc_on_v4", "__file__": VC}
exec(compile(src, VC + " (reading v4\\build_tables.py)", "exec"), g)  # prints its own report
import importlib.util  # noqa: E402

ms = importlib.util.spec_from_file_location("bt4", os.path.join(HERE, "v4", "build_tables.py"))
bt4 = importlib.util.module_from_spec(ms)
ms.loader.exec_module(bt4)
w = {k: x for k, gc, x in bt4.GATE_ROWS}
expected = sorted([
    "not a fenced spec line: %s: %r" % ("HEADER_COMMENT", bt4.HEADER_COMMENT[:120]),
    "not a fenced spec line: %s: %r" % ("CAP9", bt4.CAP9[:120]),
    "not a fenced spec line: %s: %r" % ("NOTES19[2]", bt4.NOTES19[2][:120]),
    "not a fenced spec line: %s: %r" % ("NOTES21[0]", bt4.NOTES21[0][:120]),
    "not a backticked spec text: %s: %r" % ("gate what", w["E3m"]),
    "not a backticked spec text: %s: %r" % ("gate what", w["E5"]),
])
got = sorted(g["problems"])
print("negative control: %d problems reported; exactly the six changed constants: %s" % (len(got), got == expected))
if got != expected:
    for p in sorted(set(got) ^ set(expected)):
        print("  unexpected or missing: " + p)
    sys.exit(1)
