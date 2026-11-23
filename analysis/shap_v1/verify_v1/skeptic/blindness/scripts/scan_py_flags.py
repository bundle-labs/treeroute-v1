# Every Python start in the agents' PowerShell commands, and whether it carries -I and -B.
# Usage: py -3.9 -I -B scan_py_flags.py <extract_dir> <label> [<label> ...]
import json
import os
import re
import sys

ext = sys.argv[1]
RX = re.compile(r"(?<![\w.-])(py(?:\.exe)?|python3?(?:\.exe)?)\s+((?:-[\w.]+\s+)*)", re.I)
for label in sys.argv[2:]:
    with open(os.path.join(ext, "calls_full_" + label + ".jsonl"), encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec["name"] != "PowerShell":
                continue
            cmd = (rec["input"] or {}).get("command", "")
            for m in RX.finditer(cmd):
                flags = m.group(2).split()
                ok = ("-I" in flags) and ("-B" in flags)
                if not ok:
                    a = max(0, m.start() - 40)
                    print("%s #%d flags=%s :: %s" % (label, rec["n"], flags, cmd[a:m.end() + 80].replace("\n", " | ")))
            n_py = len(RX.findall(cmd))
    print(label, "scanned")
