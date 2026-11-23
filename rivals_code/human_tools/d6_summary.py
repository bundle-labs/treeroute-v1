"""Summarise the D6 site-day downloads (read-only; run isolated with the two folders as arguments):

    py -3.9 -I D:\\treeroute\\human_tools\\d6_summary.py <pifsc folder> <pfeg folder> <out.csv>

Joins the PIFSC mirror files (crw_<n>_{dhw,baa7d,hs}.csv) and the pfeg NOAA_DHW files (dhw_<n>.csv) by site-day n,
checks every file's SHA-256 against its product_manifest.json, writes one row per site-day and prints how many
values are present and whether the two servers agree where both exist. This is NOT the D6 comparison with our
recomputed DHW (that is the R1 adapter's job); it only says what was downloaded.
"""
import csv
import hashlib
import json
import os
import sys


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def read_folder(folder):
    m = json.load(open(os.path.join(folder, "product_manifest.json"), encoding="utf-8"))
    out = {}
    for fn, rec in m["files"].items():
        p = os.path.join(folder, fn)
        if sha(p) != rec["sha256"]:
            raise SystemExit("hash mismatch %s" % p)
        rows = list(csv.reader(open(p, encoding="utf-8")))
        hdr, vals = rows[0], rows[2]
        out[fn] = dict(zip(hdr, vals))
    return out


def num(v):
    try:
        x = float(v)
        return None if x != x else x
    except (TypeError, ValueError):
        return None


def main(pifsc, pfeg, out_csv):
    a = read_folder(pifsc)
    b = read_folder(pfeg) if os.path.isdir(pfeg) else {}
    ns = sorted({fn.split("_")[1] for fn in a})
    rows = []
    for n in ns:
        r = {"n": n}
        for tag, var in (("dhw", "degree_heating_week"), ("baa7d", "bleaching_alert_area"), ("hs", "hotspot")):
            d = a.get("crw_%s_%s.csv" % (n, tag), {})
            r["pifsc_" + tag] = num(d.get(var))
            r["pixel_lat"], r["pixel_lon"], r["time"] = d.get("latitude"), d.get("longitude"), d.get("time")
        e = b.get("dhw_%s.csv" % n)
        for k in ("CRW_SST", "CRW_HOTSPOT", "CRW_DHW", "CRW_BAA", "CRW_BAA_7D_MAX"):
            r["pfeg_" + k] = num(e.get(k)) if e else None
        rows.append(r)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    have = sum(r["pifsc_dhw"] is not None for r in rows)
    both = [r for r in rows if r["pfeg_CRW_DHW"] is not None and r["pifsc_dhw"] is not None]
    agree_dhw = sum(abs(r["pfeg_CRW_DHW"] - r["pifsc_dhw"]) < 1e-6 for r in both)
    agree_baa = sum(r["pfeg_CRW_BAA_7D_MAX"] == r["pifsc_baa7d"] for r in both)
    agree_hs = sum(r["pfeg_CRW_HOTSPOT"] is not None and r["pifsc_hs"] is not None
                   and abs(r["pfeg_CRW_HOTSPOT"] - r["pifsc_hs"]) < 1e-3 for r in both)
    print("site-days %d | PIFSC DHW present %d, missing (land/mask) %d | pfeg files %d | both %d: DHW agree %d, "
          "BAA7D agree %d, HotSpot agree %d" % (len(rows), have, len(rows) - have, len(b), len(both), agree_dhw,
                                                agree_baa, agree_hs))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
