# Replace private strings (given as arguments, never stored here) by "<redacted>" in this skeptic's own files.
# Usage: py -3.9 -I -B scrub_own_files.py <folder inside V\skeptic\blindness> <string> [<string> ...]
import os
import re
import sys

root = os.path.abspath(sys.argv[1])
own = os.path.abspath(r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\blindness")
if not (root == own or root.startswith(own + os.sep)):
    raise SystemExit("refusing: %s is outside the skeptic's folder" % root)
pats = [re.compile(re.escape(s), re.I) for s in sys.argv[2:] if s]
changed = 0
for d, _, files in os.walk(root):
    for f in files:
        p = os.path.join(d, f)
        with open(p, "r", encoding="utf-8", errors="strict") as fh:
            txt = fh.read()
        new = txt
        for rx in pats:
            new = rx.sub("<redacted>", new)
        if new != txt:
            with open(p, "w", encoding="utf-8", newline="") as fh:
                fh.write(new)
            changed += 1
print("files changed:", changed)
