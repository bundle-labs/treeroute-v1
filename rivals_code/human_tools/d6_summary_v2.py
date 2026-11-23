"""Summarise and check the D6 v2 site-day download (read-only; run isolated with paths as arguments):

    py -3.9 -I D:\\treeroute\\human_tools\\d6_summary_v2.py <v2 folder> <d6_sitedays_v2.csv> <sst_compact_all.npz> <out.csv>

For every site-day of d6_sitedays_v2.csv it reads crw_<n>_{dhw,baa7d,hs,sst}.csv from the v2 folder (each file's
SHA-256 checked against product_manifest.json) and checks three things, printing the counts:
  1. DAY    the time ERDDAP returned is d* (the 'day' column) at 12:00Z, the CRW stamp.
  2. PIXEL  the latitude/longitude ERDDAP returned is the SST cache pixel (px_lat, px_lon; longitude 0..360 there).
  3. SST    NOAA's analysed_sst at that pixel and day equals our cached SST for the site on that day
            (D:/coral/drivers/sst_compact_all.npz, key = site_key(lat, lon) of coral_safe.py:97-107, days since
            1970-01-01, coral_fullscale.py:155-194). Equal SST is the proof that the pixel is the one our features
            read. Tolerance 0.006 deg C (the CSV prints 2 decimals; the cache stores them as float32).
It does NOT compare DHW with our recomputed DHW: that is the R1 adapter's job (research_coral.md:188-191).
No label is read: the site-day file holds only locations, dates and marks.
"""
import csv
import hashlib
import json
import os
import sys
import zipfile

TAGS = (("dhw", "degree_heating_week"), ("baa7d", "bleaching_alert_area"), ("hs", "hotspot"),
        ("sst", "analysed_sst"))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def num(v):
    try:
        x = float(v)
        return None if x != x else x
    except (TypeError, ValueError):
        return None


def site_key(lat, lon, dp=4):
    s = 10 ** dp
    a = int(round((float(lat) + 90.0) * s))
    b = int(round((float(lon) + 180.0) * s))
    return a * (360 * s + 1) + b


def load_cache(npz, want):
    """Our cached SST for the wanted (key, day) pairs only. Loads uk/start/end, then day/sst (~0.9 GB)."""
    import numpy as np
    with zipfile.ZipFile(npz) as zf:
        names = set(zf.namelist())
        if not {"uk.npy", "start.npy", "end.npy", "day.npy", "sst.npy"} <= names:
            raise SystemExit("unexpected npz layout in %s: %s" % (npz, sorted(names)))
    z = np.load(npz, allow_pickle=False)
    uk, st, en = z["uk"], z["start"], z["end"]
    day, sst = z["day"], z["sst"]
    out = {}
    for k, d in want:
        i = int(np.searchsorted(uk, k))
        if i >= len(uk) or int(uk[i]) != k:
            out[(k, d)] = ("no_site", None)
            continue
        dd = day[st[i]:en[i]]
        j = int(np.searchsorted(dd, d))
        if j >= len(dd) or int(dd[j]) != d:
            out[(k, d)] = ("no_day", None)
            continue
        out[(k, d)] = ("ok", float(sst[st[i] + j]))
    return out


def main(folder, sitedays, npz, out_csv):
    import datetime as dt
    man = json.load(open(os.path.join(folder, "product_manifest.json"), encoding="utf-8"))
    files = {}
    for fn, rec in man["files"].items():
        p = os.path.join(folder, fn)
        if sha(p) != rec["sha256"]:
            raise SystemExit("hash mismatch %s" % p)
        rows = list(csv.reader(open(p, encoding="utf-8")))
        files[fn] = dict(zip(rows[0], rows[2]))
    sd = list(csv.DictReader(open(sitedays, newline="", encoding="utf-8")))
    ep = dt.date(1970, 1, 1)
    want = [(site_key(r["lat"], r["lon"]), (dt.date.fromisoformat(r["day"]) - ep).days) for r in sd]
    cache = load_cache(npz, want)
    rows = []
    for r, w in zip(sd, want):
        o = {"n": r["n"], "row_id": r["row_id"], "mark": r["mark"], "row_kind": r["row_kind"], "day": r["day"],
             "day_moved_from_v1": r["day_moved_from_v1"], "px_lat": r["px_lat"], "px_lon": r["px_lon"],
             "edge": int(r["edge_lat"]) or int(r["edge_lon"])}
        got_day = got_px = True
        present = 0
        for tag, var in TAGS:
            d = files.get("crw_%s_%s.csv" % (r["n"], tag))
            if d is None:
                o[tag] = None
                got_day = got_px = False
                continue
            present += 1
            o[tag] = num(d.get(var))
            got_day &= d.get("time") == "%sT12:00:00Z" % r["day"]
            got_px &= (abs(float(d["latitude"]) - float(r["px_lat"])) < 1e-6 and
                       abs(float(d["longitude"]) - float(r["px_lon"]) % 360.0) < 1e-6)
        o["files"] = present
        o["day_ok"] = int(got_day)
        o["pixel_ok"] = int(got_px)
        status, ours = cache[w]
        o["our_sst"] = ours
        o["cache_status"] = status
        if o["sst"] is None or ours is None:
            o["sst_match"] = ""
        else:
            o["sst_match"] = int(abs(o["sst"] - ours) < 0.006)
        rows.append(o)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for mark in ("train", "test", "all"):
        rr = [o for o in rows if mark == "all" or o["mark"] == mark]
        comp = [o for o in rr if o["sst_match"] != ""]
        print("%-5s site-days %3d | all 4 files %3d | day ok %3d | pixel ok %3d | DHW present %3d | SST compared "
              "%3d, equal %3d, differ %3d | cache: no site %d, no day %d"
              % (mark, len(rr), sum(o["files"] == 4 for o in rr), sum(o["day_ok"] for o in rr),
                 sum(o["pixel_ok"] for o in rr), sum(o["dhw"] is not None for o in rr), len(comp),
                 sum(o["sst_match"] == 1 for o in comp), sum(o["sst_match"] == 0 for o in comp),
                 sum(o["cache_status"] == "no_site" for o in rr), sum(o["cache_status"] == "no_day" for o in rr)))
    edge = [o for o in rows if o["edge"]]
    for o in edge:
        print("edge site %s %s px (%s, %s): NOAA SST %s, ours %s, match %s"
              % (o["n"], o["row_id"], o["px_lat"], o["px_lon"], o["sst"], o["our_sst"], o["sst_match"]))
    bad = [o for o in rows if o["sst_match"] == 0]
    for o in bad[:20]:
        print("SST differs: %s %s day %s NOAA %s ours %s" % (o["n"], o["row_id"], o["day"], o["sst"], o["our_sst"]))


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
