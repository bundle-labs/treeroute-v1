# Which tool results mention statistic words, and what each of those calls read (to separate the agent's own
# numbers, the protocol/brief/spec text and anything else).
# Usage: py -3.9 -I -B scan_stat_words.py <extract_dir> <label> [<label> ...]
import json
import os
import re
import sys

ext = sys.argv[1]
RX = re.compile(r"kendall|spearman|\brbo\b|jaccard|tau-b|tau_b|consensus|own[-_ ]history share|\bW\s*=", re.I)
for label in sys.argv[2:]:
    print("=" * 10, label)
    with open(os.path.join(ext, "calls_full_" + label + ".jsonl"), encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            res = rec["result"] or ""
            hits = RX.findall(res)
            if not hits:
                continue
            inp = rec["input"] or {}
            what = inp.get("file_path") or inp.get("command") or inp.get("pattern") or ""
            print("#%d %s hits=%d :: %s" % (rec["n"], rec["name"], len(hits), what.replace("\n", " | ")[:230]))
