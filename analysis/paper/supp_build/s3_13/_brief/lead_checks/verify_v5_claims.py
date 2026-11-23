"""Check two data claims of fix_order_v5.md (read only).

1. NDVI: which context columns each model's meta.json merges into tree columns (duplicates_merged), and the
   'context and calendar' family of per_lead.json; the same field on the other problems.
2. Coral: how many background visits are earlier visits at the explained visit's own reef site.
Usage: py -3.9 -I -B verify_v5_claims.py
"""
import json
import os
import sys

import pyarrow.parquet as pq

OUT = r"D:\treeroute\analysis\shap_v1\out"


def meta_dups():
    for p in ("pm25", "ndvi", "fire", "defo", "coral"):
        d = os.path.join(OUT, p, "lead_0")
        for m in sorted(os.listdir(d)):
            f = os.path.join(d, m, "meta.json")
            if not os.path.isfile(f):
                continue
            with open(f, encoding="utf-8") as fh:
                meta = json.load(fh)
            dm = meta.get("duplicates_merged")
            n = len(dm) if isinstance(dm, (list, dict)) else dm
            print("%-5s %-22s duplicates_merged: %s" % (p, m, n))
            if p == "ndvi" and m == "treeroute":
                print("   ", json.dumps(dm, ensure_ascii=True)[:600])
    with open(os.path.join(OUT, "ndvi", "lead_0", "compare", "per_lead.json"), encoding="utf-8") as fh:
        pl = json.load(fh)
    fam = pl.get("families")
    if isinstance(fam, dict):
        for k, v in fam.items():
            if isinstance(v, dict):
                print("ndvi families[%s] keys: %s" % (k, sorted(v.keys())[:8]))
                cc = v.get("context and calendar")
                if cc is not None:
                    print("   context and calendar:", cc)
            elif isinstance(v, list):
                print("ndvi families[%s]: %s" % (k, v[:12]))
    else:
        print("ndvi families type:", type(fam))


def coral_same_site():
    d = os.path.join(OUT, "coral", "lead_0", "treeroute")
    bk = pq.read_table(os.path.join(d, "background_keys.parquet")).to_pydict()
    print("background_keys columns:", sorted(bk.keys()))
    rcols = [c for c in pq.ParquetFile(os.path.join(d, "rows.parquet")).schema.names if c in ("row", "unit", "time")]
    rw = pq.read_table(os.path.join(d, "rows.parquet"), columns=rcols).to_pydict()
    print("rows.parquet key columns:", rcols, "rows:", len(rw[rcols[0]]))
    row_unit = dict(zip(rw["row"], rw["unit"]))
    row_time = dict(zip(rw["row"], rw["time"])) if "time" in rw else {}
    ucol = "unit" if "unit" in bk else None
    tcol = "time" if "time" in bk else None
    if ucol is None:
        print("no unit column in background_keys; stop")
        return
    n = same = later = 0
    rows_with = set()
    for r, u, t in zip(bk["row"], bk[ucol], bk[tcol] if tcol else [None] * len(bk["row"])):
        n += 1
        site_b = str(u).split("|")[0]
        site_r = str(row_unit[r]).split("|")[0]
        if site_b == site_r:
            same += 1
            rows_with.add(r)
        if tcol and row_time and t is not None and t >= row_time[r]:
            later += 1
    print("background pairs: %d; same reef site: %d in %d sample rows; dated on/after the explained visit: %d"
          % (n, same, len(rows_with), later))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    meta_dups()
    coral_same_site()
