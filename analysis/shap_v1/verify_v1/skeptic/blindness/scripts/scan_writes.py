# Scan the content of every Write and the strings of every Edit (every version of every script an agent wrote)
# for forbidden names, plus every PowerShell command for script runs, writes and deletes.
# Usage: py -3.9 -I -B scan_writes.py <extract_dir> <label> [<label> ...]
import json
import os
import re
import sys

ext = sys.argv[1]
labels = sys.argv[2:]
TERMS = [r"compare_shap", r"shapv1_stats", r"AW3_table", r"AW4_table", r"AW4_main_row", r"pairs\.parquet",
         r"importance\.parquet", r"families\.parquet", r"bootstrap_stats", r"bardl_fix", r"smoke",
         r"verify_v1[\\/]+A\b", r"verify_v1[\\/]+B\b", r"reconcile", r"skeptic", r"tr_shap\.py", r"run_shap\.py",
         r"shap_v1[\\/]+scripts", r"subprocess", r"os\.system", r"popen", r"runpy", r"importlib", r"exec\(",
         r"\"compare\"", r"'compare'", r"/ \"compare\"", r"per_lead"]
RX = [(t, re.compile(t, re.I)) for t in TERMS]
PS_RX = [("runs a SHAP script", re.compile(r"(tr_shap|run_shap|compare_shap|rival_shap|ridge_shap|bardl_shap|tr_rebuild|make_sample|shapv1_\w+)\.py", re.I)),
         ("SHAP scripts path", re.compile(r"shap_v1[\\/]+scripts", re.I)),
         ("write/delete cmdlet", re.compile(r"\b(Remove-Item|Move-Item|Copy-Item|Rename-Item|Set-Content|Add-Content|Out-File|New-Item|Clear-Content)\b|>\s*['\"]?[A-Za-z]:", re.I))]

for label in labels:
    path = os.path.join(ext, "calls_full_" + label + ".jsonl")
    print("=" * 20, label)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            n, name, inp = rec["n"], rec["name"], rec["input"] or {}
            if name == "Write":
                texts = [("content", inp.get("content", ""))]
            elif name == "Edit":
                texts = [("old", inp.get("old_string", "")), ("new", inp.get("new_string", ""))]
            elif name == "PowerShell":
                cmd = inp.get("command", "")
                for lab, rx in PS_RX:
                    for m in rx.finditer(cmd):
                        a, b = max(0, m.start() - 90), min(len(cmd), m.end() + 90)
                        print("#%d PS %s :: %s" % (n, lab, cmd[a:b].replace("\n", " | ")))
                texts = []
            else:
                texts = []
            for where, text in texts:
                for t, rx in RX:
                    for m in rx.finditer(text):
                        # report the full source line of the match
                        ls = text.rfind("\n", 0, m.start()) + 1
                        le = text.find("\n", m.end())
                        le = len(text) if le < 0 else le
                        print("#%d %s %s %s term=%s :: %s" % (n, name, inp.get("file_path", "")[-40:], where, t,
                                                               text[ls:le].strip()[:220]))
