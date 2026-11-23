"""Read-only scan: which .py files were created by an assistant Write tool call in the session transcripts.

Usage: py -3.12 -I scan_writes.py <out_csv> <projects_dir> [<projects_dir> ...]
Writes one CSV (basename, full path written, first timestamp, number of Write calls, number of Edit calls)
to <out_csv>, which must not exist yet, and prints counts for name patterns typical of data-ingest code.
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict

PATTERNS = ("fetch", "ingest", "download", "assemble", "build_", "sample", "extract", "panel")


def main(argv):
    out_csv = argv[0]
    if os.path.exists(out_csv):
        raise SystemExit(f"refusing to overwrite {out_csv}")
    rows = defaultdict(lambda: {"first": None, "writes": 0, "edits": 0, "paths": set()})
    for root in argv[1:]:
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                if not name.endswith(".jsonl"):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        if '"tool_use"' not in line or '"type":"assistant"' not in line:
                            continue
                        try:
                            obj = json.loads(line)
                        except ValueError:
                            continue
                        if obj.get("type") != "assistant":
                            continue
                        ts = obj.get("timestamp")
                        for block in (obj.get("message") or {}).get("content") or []:
                            if not isinstance(block, dict) or block.get("type") != "tool_use":
                                continue
                            tool = block.get("name")
                            if tool not in ("Write", "Edit", "MultiEdit"):
                                continue
                            fp = (block.get("input") or {}).get("file_path") or ""
                            if not fp.lower().endswith(".py"):
                                continue
                            base = re.split(r"[\\/]", fp)[-1].lower()
                            r = rows[base]
                            r["paths"].add(fp)
                            if tool == "Write":
                                r["writes"] += 1
                                if ts and (r["first"] is None or ts < r["first"]):
                                    r["first"] = ts
                            else:
                                r["edits"] += 1
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["basename", "first_write_utc", "writes", "edits", "paths"])
        for base in sorted(rows):
            r = rows[base]
            w.writerow([base, r["first"], r["writes"], r["edits"], " | ".join(sorted(r["paths"]))])
    written = [b for b, r in rows.items() if r["writes"] > 0]
    print(f".py basenames with an assistant Write call: {len(written)}; with Edit only: {sum(1 for r in rows.values() if r['writes'] == 0)}")
    for pat in PATTERNS:
        names = sorted(b for b in written if pat in b)
        print(f"  '{pat}': {len(names)}  e.g. {', '.join(names[:12])}")


if __name__ == "__main__":
    main(sys.argv[1:])
