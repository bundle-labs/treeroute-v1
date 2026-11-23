import sys, json, os
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(os.path.dirname(HERE), "cells.json"), "r", encoding="utf-8") as f:
    d = json.load(f)
E = d["entries"]
def show(pred, n=4):
    k = 0
    for e in E:
        if pred(e):
            print(json.dumps(e, ensure_ascii=False))
            k += 1
            if k >= n:
                break
show(lambda e: e["table"] == "S3.19" and e["column"] == "background_rows", 6)
show(lambda e: e["table"] == "S3.19" and e["row"] == "note", 3)
show(lambda e: e["table"] == "S3.20" and e["row"] == "note", 3)
show(lambda e: e["table"] == "S3.20" and e["column"] == "s_exact", 3)
show(lambda e: e["table"] == "S3.21" and e["row"] in ("E3m", "E9"), 4)
show(lambda e: e["table"] == "S3.24" and e["row"] == "note", 20)
show(lambda e: e["table"] == "S3.25" and e["column"] == "sign_agreement_top10" and e["panel"] == "a", 12)
show(lambda e: e["table"] == "S3.25" and e["panel"] == "c", 4)
show(lambda e: e["table"] == "S3.23" and e["panel"] == "b" and e["column"] == "tvd_family", 2)
show(lambda e: e["table"] == "S3.27" and e["panel"] == "f", 2)
show(lambda e: e["table"] == "S3.27" and e["panel"] == "g", 2)
show(lambda e: e["table"] == "S3.28" and e["panel"] == "b" and e["row"] in ("tv_family_shares", "jaccard_top20", "n_J"), 6)
show(lambda e: e["table"] == "S3.29" and e["row"] == "top3", 3)
show(lambda e: e["table"] == "S3.30", 20)
show(lambda e: e["table"] == "9" and e["row"] == "fire", 5)
show(lambda e: e["table"] == "S3.22" and e["row"] in ("spearman_per_rival", "own_history_per_rival") and e["column"] == "coral", 6)
from collections import Counter
print(Counter((e["table"]) for e in E))
print(Counter((e["part"]) for e in E))
