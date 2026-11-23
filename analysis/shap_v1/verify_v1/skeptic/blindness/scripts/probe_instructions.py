# What the harness injected as "instructions" (memory / CLAUDE.md files) into one transcript: file names, sizes and
# whether the text mentions comparison statistics. Prints no file content; writes nothing.
# Usage: py -3.9 -I -B probe_instructions.py <transcript.jsonl>
import json
import os
import re
import sys

RX = re.compile(r"kendall|spearman|\brbo\b|jaccard|AW4_main_row|AW4_table|AW3_table|main[- ]text row|"
                r"own[- ]history share|\bW\s*[=:]\s*-?\d|consensus top", re.I)
with open(sys.argv[1], encoding="utf-8") as fh:
    for line in fh:
        obj = json.loads(line)
        if obj.get("type") != "attachment":
            continue
        att = obj.get("attachment") or {}
        if att.get("type") != "instructions":
            continue
        for f in att.get("files", []):
            txt = f.get("content", "") or ""
            hits = sorted(set(m.group(0).lower() for m in RX.finditer(txt)))
            print("file:", os.path.basename(f.get("path", "")), "| kind:", f.get("type"), "| chars:", len(txt),
                  "| statistic words:", hits)
