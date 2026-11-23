"""Report check 3: how many runs of reconcile.py the open logs show. Prints, per second, how many compare
files reconcile.py opened (opened_official.jsonl) and how many run records (opened_other.jsonl), and per
cluster which of the 50 compare files were opened and how often. Read-only.
Run: py -3.9 -I -B c02b_run_seconds.py
"""
import collections
import json
import os

W = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile\work"


def load(name):
    with open(os.path.join(W, name), encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def main():
    off = load("opened_official.jsonl")
    oth = load("opened_other.jsonl")
    per_sec = collections.OrderedDict()
    for r in off:
        if r["by"].startswith("reconcile.py"):
            k = r["time"][11:19]
            per_sec.setdefault(k, collections.Counter())[r["by"]] += 1
    for r in oth:
        k = r["time"][11:19]
        per_sec.setdefault(k, collections.Counter())["other:" + r["by"]] += 1
    for k in sorted(per_sec):
        print(k, dict(per_sec[k]))
    print()
    # per second: the multiplicity of each compare file opened by reconcile.py (plain opens)
    files_per_sec = collections.defaultdict(collections.Counter)
    for r in off:
        if r["by"] == "reconcile.py":
            files_per_sec[r["time"][11:19]][r["file"].split("\\")[-1]] += 1
    for k in sorted(files_per_sec):
        c = files_per_sec[k]
        print(k, "plain opens:", sum(c.values()), "| by file name:", dict(c))
    # the first opened per problem in each second, to see where a run starts (coral first?)
    print()
    order = collections.defaultdict(list)
    for r in off:
        if r["by"] == "reconcile.py":
            order[r["time"][11:19]].append(r["file"].split("\\")[2] + "/" + r["file"].split("\\")[-1])
    for k in sorted(order):
        seq = order[k]
        print(k, "first:", seq[0], "| last:", seq[-1], "| n:", len(seq))


if __name__ == "__main__":
    main()
