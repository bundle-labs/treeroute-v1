# Compact listing of every tool call plus a scan of inputs and results for forbidden names.
# Usage: py -3.9 -I -B scan_calls.py <extract_dir> <label> [<label> ...]
# Reads only the scrubbed extracts written by extract_calls.py.
import json
import os
import re
import sys

ext = sys.argv[1]
labels = sys.argv[2:]

TERMS = [
    r"compare_shap", r"shapv1_stats", r"AW3_table", r"AW4_table", r"AW4_main_row", r"pairs\.parquet",
    r"importance\.parquet", r"families\.parquet", r"bootstrap_stats", r"bardl_fix", r"per_lead",
    r"verify_v1[\\/]+A\b", r"verify_v1[\\/]+B\b", r"verify_v1[\\/]+reconcile", r"verify_v1[\\/]+skeptic",
    r"[\\/]compare[\\/]", r"tr_shap\.py", r"run_shap\.py", r"shap_v1[\\/]+scripts", r"SHAP[\\/]+scripts",
    r"[\\/]smoke", r"pairs\.parquet\.done",
]
RX = [(t, re.compile(t, re.I)) for t in TERMS]


def compact(name, inp):
    if name == "Read":
        return "Read %s off=%s lim=%s" % (inp.get("file_path"), inp.get("offset"), inp.get("limit"))
    if name == "Grep":
        return "Grep pat=%r path=%s glob=%s type=%s mode=%s" % (inp.get("pattern"), inp.get("path"), inp.get("glob"),
                                                                inp.get("type"), inp.get("output_mode"))
    if name == "Glob":
        return "Glob pat=%r path=%s" % (inp.get("pattern"), inp.get("path"))
    if name == "PowerShell":
        return "PS " + inp.get("command", "")
    if name in ("Write", "Edit"):
        return "%s %s" % (name, inp.get("file_path"))
    return "%s %s" % (name, json.dumps(inp)[:200])


for label in labels:
    path = os.path.join(ext, "calls_full_" + label + ".jsonl")
    out_list = os.path.join(ext, "compact_" + label + ".txt")
    out_scan = os.path.join(ext, "scan_" + label + ".txt")
    with open(path, encoding="utf-8") as fh, open(out_list, "w", encoding="utf-8") as fl, \
            open(out_scan, "w", encoding="utf-8") as fs:
        for line in fh:
            rec = json.loads(line)
            n, name, inp, res = rec["n"], rec["name"], rec["input"] or {}, rec["result"] or ""
            fl.write("#%d %s [%s out=%d%s]\n   %s\n" % (n, rec["ts"][11:19], name, len(res),
                                                    " ERR" if rec["is_error"] else "", compact(name, inp)))
            inp_text = json.dumps(inp, ensure_ascii=False)
            if name == "Write":
                # the content of a written script is scanned separately (scripts are read in full)
                inp_text = json.dumps({k: v for k, v in inp.items() if k != "content"}, ensure_ascii=False)
            for where, text in (("IN", inp_text), ("OUT", res)):
                for t, rx in RX:
                    for m in rx.finditer(text):
                        a, b = max(0, m.start() - 120), min(len(text), m.end() + 120)
                        fs.write("#%d %s %s term=%s :: %s\n" % (n, name, where, t, text[a:b].replace("\n", " | ")))
    print(label, "->", out_list, out_scan)
